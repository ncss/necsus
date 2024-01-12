let plainTextRenderer = new PlainTextRenderer;
const NEW_MESSAGE_HISTORY_SIZE = 20;
const ACTIVE_STYLESHEETS = new Map();  // Maps URLs to <link> DOM elements.
const ACTIVE_SCRIPTS = new Map();      // Maps URLs to <script> DOM elements.

const EXT_RESOURCE_TAGS = [
  ['img', 'src'],
  ['embed', 'src'],
  ['object', 'data'],
  ['link', 'href'],
  ['script', 'src'],
  ['audio', 'src'],
  ['video', 'src'],
];

let Necsus = new Vue({
  el: '#necsus',
  data: {
    room: '',
    settings: {},
    clearRoomShow: false,
    clearRoomConfirm: "",
    bots: [],
    importing: {
      text: '',
      importBots: null,
      installedBots: [],
    },
    messages: [],
    messagesById: new Map(),
    toPostprocessMessages: [],
    modals: {},
    newMessage: '',
    newMessageHistory: [],      // For up-arrow back-going.
    newMessageHistoryPos: 0,    // For up-arrow back-going.
    sendingMessage: false,
    statePresent: false,
    replyToBotName: undefined,
    websocketConnected: false,  // UI indicator.
    websocketRetries: 0,        // Used for exponential backoff on reconnects.
    lectureMode: false,         // Hide room name during lectures

    messageListeners: new Map(),  // Maps user-installed functions to lists of yet-to-be-processed messages.
  },
  created: function() {
    let vm = this;

    try {
      // Try to load previous settings.
      let oldsettings = JSON.parse(window.localStorage.getItem("settings"));
      if (oldsettings.open === undefined ||
          oldsettings.name === undefined ||
          oldsettings.speech === undefined)
        throw null;
      vm.settings = oldsettings;
    } catch {
      // Default settings.
      vm.settings = {
        open: false,
        name: 'Anonymous',
        // TODO: Make this a tertiary state where we have an "auto" and the
        //       default state is with TTS only happening if the user used STT.
        speech: false,
      };
    }

    /*
      Determine the room
    */
    vm.room = decodeURIComponent(window.location.pathname.slice(1));
    document.title = `NeCSuS | ${vm.room}`

    // Updates (new messages, put/delete bots, clearing room, etc) all come over a websocket.
    vm.createWebsocket();


    /*
      Speech recognition
    */
    if (window.webkitSpeechRecognition) {
      let recognition = new webkitSpeechRecognition();
      vm.speechRecognition = recognition;

      recognition.lang = 'en-AU';
      recognition.interimResults = true;
      recognition.continuous = false;
      recognition.maxAlternatives = 1;

      recognition.onresult = function(event) {
        let firstResult = event.results[0];
        let firstAlternative = firstResult[0];

        vm.speechRecognitionResult({
          result: firstAlternative.transcript,
          isFinal: firstResult.isFinal,
        });
      };
    }
  },
  mounted: function() {
    document.addEventListener('keydown', (event) => {
      if (event.code === 'Escape') {
        (document.querySelectorAll('.modal') || []).forEach(($modal) => {
          $modal.classList.remove('is-active');
        });    
      }
    });
    this.$refs.import_selector.addEventListener('change', function (event) {
      const fileList = event.target.files;
      if (fileList.length > 0) {
        const reader = new FileReader();
        reader.addEventListener('load', function (event) {
          this.importing.text = event.target.result;
          this.$refs.import_selector.value = null;
          // TODO: It would be nice to resize the textarea here
        }.bind(this));
        reader.readAsText(fileList[0]);
      }
    }.bind(this));
  },
  updated: function() {
    // We need to post-process messages, to redirect the forms, and eval the <script> tags.
    // However, this updated() function is run every time the whole Vue component (the chatroom)
    // updates, rather than when a message is inserted. So there might be a case where we have
    // new messages to postprocess, but they have not reached the DOM yet. We need to be careful
    // to only eval the ones that have reached the DOM.

    // Find the messages to process that have reached the DOM on this update cycle.
    let reachedDom = new Map()
    for (let message of this.toPostprocessMessages) {
      let domElt = document.querySelector(`div[necsus-message-id="${message.id}"]`)
      if (domElt !== null)
        reachedDom.set(message.id, {message, domElt})
    }

    // First we are going to post-process the forms to attach our custom submit handlers,
    // for the form interactions with necsus.
    for (let {message, domElt} of reachedDom.values()) {
      domElt.querySelectorAll('form').forEach((formElt) => {
        formElt.addEventListener('submit', (e) => this.formMessageSubmit(e))
        formElt.dataset.from_bot = message.from_bot
      })
    }

    // Take any new CSS stylesheets which were attached to messages, and hoist them into a <link> in the <head>.
    for (let {message, domElt} of reachedDom.values()) {
      if (message.css != null && !ACTIVE_STYLESHEETS.has(message.css)) {
        let link = document.createElement('link');
        link.setAttribute('rel', 'stylesheet');
        link.setAttribute('href', urljoin(message.base_url, message.css));

        console.log(`Inserting stylesheet into <head> from ${message.id}: ${link.outerHTML}`);
        document.head.appendChild(link);
        ACTIVE_STYLESHEETS.set(message.css, link);
      }
    }

    // Take any new JS scripts which were attached to messages, and hoist them into a <link> in the <head>.
    for (let {message, domElt} of reachedDom.values()) {
      if (message.js != null && !ACTIVE_SCRIPTS.has(message.js)) {
        let script = document.createElement('script')
        script.setAttribute('src', urljoin(message.base_url, message.js))
        script.setAttribute('type', message.js.endsWith('.mjs') ? 'module' : 'text/javascript')
        script.setAttribute('async', true)

        console.log(`Inserting script into <head> from ${message.id}: ${script.outerHTML}`);
        document.head.appendChild(script);
        ACTIVE_SCRIPTS.set(message.js, script);
      }
    }

    // Take any tags which reference external resources, and relativise them as well.
    for (let {message, domElt} of reachedDom.values()) {
      for (let [tag, attr] of EXT_RESOURCE_TAGS) {
        domElt.querySelectorAll(tag).forEach((el) => {
          if (el.hasAttribute(attr)) {
            el.setAttribute(attr, urljoin(message.base_url, el.getAttribute(attr)));
          }
        });
      }
    }

    // Welcome, and congratulations for looking into this. The following code
    // makes <script> tags in messages act as though it was XSS in 2005
    // (namely, it works and the browser can't detect it). Modern browsers have
    // really annoying sophisticated system for detecting XSS and blocking it.
    // Unfortunately for us, XSS is a key feature of NeCSuS so we have to run
    // eval() on the <script> tags ourselves.

    // For each not-yet-eval()ed script, run it in the order received (noting
    // that several script tags can exist in a message).
    for (let {message, domElt} of reachedDom.values()) {
      domElt.querySelectorAll('script').forEach((script) => {
        console.log(`Manually eval()ing message ${message.id} to get around Chrome XSS blocking...`);
        script.type = "text/gzip";
        window.eval(script.innerHTML);
      })
    }

    // Clear the messages we've processed.
    this.toPostprocessMessages = this.toPostprocessMessages.filter(({id}) => !reachedDom.has(id));

    // Fire event listeners on anything for external Javascript hooks.
    this.runEventListeners();
  },
  methods: {
    openCopyConfModal: function () {
      this.$refs.copy_conf_modal.classList.add('is-active');
    },
    closeCopyConfModal: function () {
      this.$refs.copy_conf_modal.classList.remove('is-active');
    },
    openPasteConfModal: function () {
      this.$refs.paste_conf_modal.classList.add('is-active');
    },    
    closePasteConfModal: function () {
      this.$refs.paste_conf_modal.classList.remove('is-active');
      // Reset importing state
      this.importing = {
        text: '',
        importBots: null,
        installedBots: [],
      }
    },
    formMessageSubmit: async function(e) {
      // Prevent form submission
      e.preventDefault()

      // Get the action URL of the form to send to the server.
      // We need to use getAttribute since otherwise it might prepend the current domain.
      let form = e.target
      let actionUrl = form.getAttribute('action')

      // Get the form data to send to the server. Usually when a named submit button is clicked,
      // that (name, value) pair would also appear in the form data. Using this method, we need
      // to put it in there ourselves.
      let data = Object.fromEntries(new FormData(form))
      if (e.submitter.name)
        data[e.submitter.name] = e.submitter.value

      // Submit to our alternate endpoint via AJAX.
      this.sendingMessage = true;
      await fetch('/api/actions/message-form', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          room: this.room,
          author: this.settings.name,
          bot_id: parseInt(form.dataset.from_bot, 10),
          action_url: actionUrl,
          form_data: data,
        }),
      })
      this.sendingMessage = false;
    },
    clearRoom: async function() {
      let response = await fetch('/api/actions/clear-room-messages', {
        method: 'POST',
        body: JSON.stringify({room: this.room}),
        headers: {'Content-Type': 'application/json'},
      });

      this.messages = [];
      this.messagesById = new Map();
      this.clearListenerQueues();

      this.clearRoomShow = false;
      this.clearRoomConfirm = "";
    },
    // Now unused
    fetchBots: async function() {
      let response = await fetch('/api/bots?' + new URLSearchParams({room: this.room}));
      let bots = await response.json();
      this.bots = bots;
    },
    // putBot installs a new or updated bot into the bot list.
    putBot: function(bot) {
      let idx = this.bots.findIndex((x) => bot.id == x.id)
      Vue.set(this.bots, (idx >= 0) ? idx : this.bots.length, bot)
    },
    deleteBot: function(bot) {
      let idx = this.bots.findIndex((x) => bot.id == x.id)
      if (idx >= 0)
        this.bots.splice(idx, 1)
    },
    botWithId: function(id) {
      for (let i = 0; i < this.bots.length; i++) {
        if (this.bots[i].id == id) {
          return this.bots[i]
        }
      }
      return null
    },
    addBot: function() {
      // GH-style names w. animals, eg. Owl-Cod-Otter
      const animals = ["Aardvark", "Alligator", "Alpaca", "Anaconda", "Ant", "Anteater", "Antelope", "Aphid",
                       "Armadillo", "Asp", "Baboon", "Badger", "Barracuda", "Bass", "Bat", "Beaver", "Bedbug",
                       "Bee", "Bee-eater", "Bird", "Bison", "Bobcat", "Buffalo", "Butterfly", "Buzzard",
                       "Camel", "Carp", "Cat", "Caterpillar", "Catfish", "Cheetah", "Chicken", "Chimpanzee",
                       "Chipmunk", "Cobra", "Cod", "Condor", "Cougar", "Cow", "Coyote", "Crab", "Cricket",
                       "Crocodile", "Crow", "Cuckoo", "Deer", "Dinosaur", "Dog", "Dolphin", "Donkey", "Dove",
                       "Dragonfly", "Duck", "Eagle", "Eel", "Elephant", "Emu", "Falcon", "Ferret", "Finch",
                       "Fish", "Flamingo", "Flea", "Fly", "Fox", "Frog", "Goat", "Goose", "Gopher", "Gorilla",
                       "Hamster", "Hare", "Hawk", "Hippopotamus", "Horse", "Hummingbird", "Husky", "Iguana",
                       "Impala", "Kangaroo", "Lemur", "Leopard", "Lion", "Lizard", "Llama", "Lobster", "Margay",
                       "Monkey", "Moose", "Mosquito", "Moth", "Mouse", "Mule", "Octopus", "Orca", "Ostrich",
                       "Otter", "Owl", "Ox", "Oyster", "Panda", "Parrot", "Peacock", "Pelican", "Penguin",
                       "Perch", "Pheasant", "Pig", "Pigeon", "Porcupine", "Quagga", "Rabbit", "Raccoon", "Rat",
                       "Rattlesnake", "Rooster", "Seal", "Sheep", "Skunk", "Sloth", "Snail", "Snake", "Spider",
                       "Tiger", "Whale", "Wolf", "Wombat", "Zebra"]
      const shuffled = animals
                      .map(x => ({x, sort: Math.random()}))
                      .sort((a, b) => a.sort - b.sort)
                      .map(({x}) => x)
      const selected = shuffled.slice(0, 3);
      let newBot = {
        name: `${selected.join("-")}`,
        url: '',
        responds_to: '',
      };
      this.submitBot(newBot);
    },
    removeBot: async function(bot) {
      if (!bot.id)
        return

      let response = await fetch('/api/actions/bot', {
        method: 'DELETE',
        body: JSON.stringify({id: bot.id}),
        headers: {'Content-Type': 'application/json'},
      })
      let botResult = await response.json();
    },
    submitBot: async function(bot, noupdate) {
      let response = await fetch('/api/actions/bot', {
        method: 'POST',
        body: JSON.stringify({
          room: this.room,
          name: bot.name,
          url: bot.url,
          responds_to: bot.responds_to,
          ...((bot.id) ? {id: bot.id} : {}),  // Only added if bot.id is present.
        }),
        headers: {'Content-Type': 'application/json'},
      })
      let botResult = await response.json();
    },
    /** Inserts a message object (recieved from the server) into the chat room. */
    insertMessage: function(message) {
      this.statePresent = message.state != null;
      if (this.statePresent) {
        let bot = this.botWithId(message.from_bot)
        this.replyToBotName = message.author || '???';
      }

      this.toPostprocessMessages.push(message)
      this.messages.push(message)
      this.messagesById.set(message.id, message)
      this.enqueueMessageIdForListeners(message.id)
    },
    createWebsocket: function() {
      let last_id = (this.lastMessage) ? this.lastMessage.id : -1
      let ws_uri = `${location.protocol == 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/${this.room}?since=${last_id}`
      console.log(`Connecting to websocket ... (${ws_uri})`)
      let ws = new WebSocket(ws_uri)
      this.ws = ws

      ws.onopen = (e) => {
        this.websocketConnected = true
        this.websocketRetries = 0
        console.log('Websocket connected')
      }

      ws.onmessage = (e) => {
        console.log('Websocket message:', e.data)
        let response = JSON.parse(e.data)
        if (response.kind == 'message')
          this.insertMessage(response.data)
        else if (response.kind == 'put_bot')
          this.putBot(response.data)
        else if (response.kind == 'delete_bot')
          this.deleteBot(response.data)
        else if (response.kind == 'clear_messages') {
          this.messages = []
          this.messagesById = new Map()
          Necsus.clearListenerQueues()
        }
      }

      ws.onerror = (e) => {
        console.log('Websocket error:', e)
      }

      // When the websocket closes (which also happens on error), retry with exponential backoff and some randomness.
      // The combination of randomness and exponential backoff allow the server to come back up gracefully on a reboot
      // without getting crushed by a zillion coordinated requests.
      ws.onclose = (e) => {
        this.websocketConnected = false
        this.websocketRetries += 1
        let retryTime = 500 * Math.pow(2, this.websocketRetries) * (1 + Math.random())
        console.log(`Websocket closed, will retry after ${retryTime} ms`)
        setTimeout(() => this.createWebsocket(), retryTime)
      }
    },
    // Kick the websocket off for a few seconds to simulate a disconnect (for testing purposes).
    // This can be done by double-clicking the connected/disconnected status indicator in the UI.
    kickWebSocket: function() {
      if (this.ws && this.ws.readyState == WebSocket.OPEN) {
        console.log('Kicking off the websocket for a while')
        this.websocketRetries = 3
        this.ws.close()
      }
    },
    submitMessage: async function() {
      if (this.newMessage.length <= 0) {
        return;
      }
      this.sendingMessage = true;

      try {
        let response = await fetch('/api/actions/message', {
          method: 'POST',
          body: JSON.stringify({
            room: this.room,
            author: this.settings.name,
            text: this.newMessage,
          }),
          headers: {'Content-Type': 'application/json'},
        });

        let messageResult = await response.json();
        console.log('Response from sending message:', messageResult)
      } catch {}
      this.sendingMessage = false;

      if (this.newMessageHistory.indexOf(this.newMessage) < 0) {
        this.newMessageHistory = [this.newMessage, ...this.newMessageHistory.slice(0, NEW_MESSAGE_HISTORY_SIZE - 1)];
      }
      this.newMessageHistoryPos = 0;
      this.newMessage = '';
    },
    newMessageHistoryMove: function(direction) {
      let inBounds = (pos) => (0 <= pos && pos <= this.newMessageHistory.length)
      if (inBounds(this.newMessageHistoryPos)) {
        this.newMessage = this.newMessageHistory[this.newMessageHistoryPos]
        let newPos = this.newMessageHistoryPos + direction
        if (inBounds(newPos))
          this.newMessageHistoryPos = newPos
      }
    },
    clearState: async function() {
      this.sendingMessage = true;
      let response = await fetch('/api/actions/clear-room-state', {
        method: 'POST',
        body: JSON.stringify({room: this.room}),
        headers: {'Content-Type': 'application/json'},
      })
      await response.json();

      this.sendingMessage = false;
    },
    speak: function(text) {
      if (this.settings.speech) {
        let utterance = new SpeechSynthesisUtterance(text);
        speechSynthesis.speak(utterance);
      }
    },
    listen: function() {
      this.speechRecognition.start()
    },
    speechRecognitionResult: function(speech) {
      this.newMessage = speech.result;
      if (speech.isFinal)
        this.submitMessage();
    },
    markdownToText(text) {
      return marked(text, {renderer: plainTextRenderer, smartypants: true});
    },
    lines: function(text) {
      text = text || '';
      return text.split(/\r\n|\r|\n/);
    },
    rows: function() {
      let message = this.newMessage || '';
      return this.lines(message).length;
    },
    toggleState: function(message) {
      Vue.set(message, 'showState', !message.showState)
      return message.showState;
    },
    setLectureMode() {
      if (!this.lectureMode) {
        history.pushState({}, "", "/");
        document.title = "NeCSuS"
        this.lectureMode = true
      }
    },

    // Focus the message input box. Optionally set the message there too (for bots to use).
    focusMessageInput: function(text) {
      if (text) {
        this.newMessage = text;
      }
      let vm = this;
      setTimeout(function() { vm.$el.querySelector('#message-input').focus() });
    },

    // Public function: use this hook!
    addEventListener(kind, fn) {
      // Only handled type currently is 'message'.
      if (kind == 'message') {
        this.messageListeners.set(fn, this.messages.map(({id}) => id))
      } else {
        throw new Error(`Unrecognised event kind '${kind}' in Necsus.addEventListener()`);
      }

      this.runEventListeners()
    },

    // Private function.
    runEventListeners() {
      for (let [fn, ids] of this.messageListeners.entries()) {
        let remaining = []
        for (let id of ids) {
          // Run all the events for messages which have reched the DOM.
          let domElt = document.querySelector(`div[necsus-message-id="${id}"]`)
          if (domElt !== null)
            fn(domElt, this.messagesById.get(id))
          else
            remaining.push(id)
        }

        this.messageListeners.set(fn, remaining)
      }
    },

    // Private function.
    clearListenerQueues() {
      for (let fn of this.messageListeners.keys())
        this.messageListeners.set(fn, [])
    },

    // Private function.
    enqueueMessageIdForListeners(id) {
      for (let value of this.messageListeners.values())
        value.push(id)
    },

    messageClass: function(message) {
      return [
        // TODO: Handle messages which weren't sent by the current session.
        //       Though that might be overkill for a somewhat minor UX feature.
        message.author == this.settings.name ? "message-right" : "message-left",
        `kind-${message.kind}`,
      ]
    },

    /* Room Downloading */
    downloadBlob: function(blob, filename) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = filename || 'download';

      const clickHandler = () => {
        setTimeout(() => {
          URL.revokeObjectURL(url);
          a.removeEventListener('click', clickHandler);
        }, 150);
      };

      a.addEventListener('click', clickHandler, false);
      a.click();

      return a;
    },
    get_exportable_text: function(obj) {
      return JSON.stringify(
        obj.map((o) => ({
          name: o.name,
          responds_to: o.responds_to,
          url: o.url
        })), null, 2);
    },
    download: function(obj) {
      const blob = new Blob([this.get_exportable_text(obj)], {type: 'application/json'});
      this.downloadBlob(blob, `necsus_export_${this.room || 'base'}.json`);
    },
    copy_to_clipboard: function(obj) {
      navigator.clipboard.writeText(this.get_exportable_text(obj));
    },

    /* Room Uploading */
    validateBots: function() {
      this.importing.errors = [];

      let bots = null;
      try {
        bots = JSON.parse(this.importing.text);
      } catch {
        this.importing.errors.push("Could not parse JSON import text.");
        return;
      }

      const bad_bots = bots.filter(
        function (bot) {
          return !('name' in bot && 'responds_to' in bot && 'url' in bot);
        }
      );
      if (bad_bots.length) {
        bots.forEach(function (bot) {
          this.importing.errors.push(`The bot ${bot.name || 'without a name'} does not have the required properties.`);
        }.bind(this));
        return;
      }
      this.importing.installedBots = this.bots.map(function(bot_copy) {
        let b = Object.assign({}, bot_copy);
        b.isIdentical = bots.some(function (oldb) {
          return b.url == oldb.url && b.responds_to == oldb.responds_to && b.name == oldb.name;
        });
        b.doImport = b.isIdentical || !bots.some(function (oldb) {
          return b.url == oldb.url || b.responds_to == oldb.responds_to || b.name == oldb.name;
        });
        return b;
      });

      this.importing.importBots = bots.map(function(bot_copy) {
        let b = Object.assign({}, bot_copy);
        b.isIdentical = this.importing.installedBots.some(function (oldb) {
          return b.url == oldb.url && b.responds_to == oldb.responds_to && b.name == oldb.name;
        });
        b.doImport = !b.isIdentical;
        return b;
      }.bind(this));
    },
    installBots: function() {
      this.importing.importBots.forEach(function(b) {
        if (!b.doImport)
          return;
        // so we need to import them.
        this.submitBot(b, true);
      }.bind(this));

      this.importing.installedBots.forEach(function(b) {
        if (b.doImport)
          return;
        // so we need to remove them.
        this.removeBot(b);
      }.bind(this));

      this.fetchBots().then(function() {
        this.closePasteConfModal();
      }.bind(this))
    }
  },
  computed: {
    lastMessage: function() {
      if (this.messages.length > 0) {
        return this.messages[this.messages.length-1];
      } else {
        return undefined;
      };
    },
    displayMessages: function () {
      let messages = this.messages.slice().reverse();
      // in previous versions of the server, time was saved as X:XX am/pm
      // for backwards compatibility, if you can't turn the `when` into
      // a Number, then just display it.
      return messages.map(function(m) {
        if (/^[0-9]+\.?[0-9]*$/.test(m.when)) {
          let date = parseFloat(m.when) * 1000;
          m['displayTime'] = timeago.format(date, 'en_US', {minInterval: 60});
          if (/seconds/.test(m['displayTime'])) {
            m['displayTime'] = 'just now';
          }
        } else {
          m['displayTime'] = m.when
        }
        return m;
      })
    }
  },
  watch: {
    settings: {
      handler: function(newSettings, _) {
        window.localStorage.setItem("settings", JSON.stringify(newSettings));
      },
      deep: true,
    },
    sendingMessage: function(sending, wasSending) {
      // Focus on the message input after sending a message input
      // But only if we aren't typing in another input
      if (wasSending && !sending && document.activeElement == document.body)
        this.focusMessageInput();
    }
  }
});

/** Absolutify {url} relative to {base_url}. If {url} is already absolute, it is left alone. */
function urljoin(base_url, url) {
  if (!base_url) {
    return url;
  }
  try {
    return new URL(url, base_url).href;
  } catch (error) {
    return url;
  }
}

// Let's test this sucker because I don't know exactly all the edge cases.
const URLJOIN_TESTS = [
  // Empty/null base url should mean {url} is passed through.
  [null, 'https://absolute.com/foo', 'https://absolute.com/foo'],
  ['', 'https://absolute.com/foo', 'https://absolute.com/foo'],
  ['', 'relative/url', 'relative/url'],

  // Invalid base url should mean {url} is passed through.
  ['garbledefoo', 'https://absolute.com/foo', 'https://absolute.com/foo'],
  ['not/a/base/url', 'relative/url', 'relative/url'],

  // The actual correct case works.
  ['http://bot.com/mybot/path', 'http://absolute.com/static/image.png', 'http://absolute.com/static/image.png'],
  ['http://bot.com/mybot/path', '/static/image.png', 'http://bot.com/static/image.png'],
  ['http://bot.com/mybot/path', 'static/image.png', 'http://bot.com/mybot/static/image.png'],
];
for (let [base_url, url, expected] of URLJOIN_TESTS) {
  let result = urljoin(base_url, url);
  if (expected !== result) {
    console.error(`Test failed: urljoin(${base_url}, ${url}) => ${result}, should have been ${expected}`);
  }
}
