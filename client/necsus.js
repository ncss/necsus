let plainTextRenderer = new PlainTextRenderer;
let app = new Vue({
  el: '#necsus',
  data: {
    room: '',
    settings: {},
    resetRoomShow: false,
    resetRoomConfirm: "",
    bots: [],
    importing: {
      text: '',
      importBots: null,
      installedBots: [],
    },
    messages: [],
    toEvalMessages: [],
    modals: {},
    newMessage: '',
    sendingMessage: false,
    statePresent: false,
    replyToBotName: undefined,
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
    vm.room = window.location.pathname.slice(1);

    /*
      Fetch the room's messages and settings
    */
    vm.fetchBots();
    vm.fetchMessages({silent: true});

    /*
      Auto update message every few seconds
    */
    vm.autoUpdate();


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
    this.modals = {
      'paste_conf_modal': M.Modal.init(this.$refs.paste_conf_modal, {
        onCloseEnd: function() {
          // Clear importing state.
          this.importing = {text: '', importBots: null, installedBots: []};
        }.bind(this),
      }),
      'copy_conf_modal': M.Modal.init(this.$refs.copy_conf_modal),
    };

    this.$refs.import_selector.addEventListener('change', function (event) {
      const fileList = event.target.files;
      if (fileList.length > 0) {
        const reader = new FileReader();
        reader.addEventListener('load', function (event) {
          this.importing.text = event.target.result;
          this.$refs.import_selector.value = null;
          this.$nextTick(function() {
            M.textareaAutoResize(this.$refs.import_text);
          }.bind(this));
        }.bind(this));
        reader.readAsText(fileList[0]);
      }
    }.bind(this));
  },
  updated: function() {
    let vm = this;

    // Welcome, and congratulations for looking into this. The following code
    // makes <script> tags in messages act as though it was XSS in 2005
    // (namely, it works and the browser can't detect it). Modern browsers have
    // really annoying^Wsophisticated system for detecting XSS and blocking it.
    // Unfortunately for us, XSS is a key feature of NeCSuS so we have to run
    // eval() on the <script> tags ourselves.

    // What is the mapping from (message-id) --> [<script>]?
    let scriptMap = {};
    Array.from(document.getElementsByClassName("message"))
         .forEach(function(elem) {
           let id = elem.attributes["necsus-message-id"].value;
           scriptMap[id] = Array.from(elem.getElementsByTagName("script"));
         });

    // For each not-yet-eval()ed script, run it in the order received (noting
    // that several script tags can exist in a message).
    for (message of vm.toEvalMessages) {
      let scripts = scriptMap[`${message.id}`];
      if (scripts === undefined) {
        continue;
      }
      scripts.forEach(function(elem, idx) {
        // This is a fairly dodgy way of marking the script as "executed" so
        // we don't run it twice. There is no disabled attribute (we could add
        // a fake one but this makes sure the DOM doesn't render it by
        // accident as well).
        if (elem.type === "text/gzip") {
          console.log(`Re-exec of existing <script>-${idx} in message ${message.id} skipped...`);
          return;
        }
        elem.type = "text/gzip";

        // TODO: Handle src=.
        console.log(`Manually eval()ing message ${message.id} <script>-${idx} to get around Chrome XSS blocking...`);
        window.eval(elem.innerHTML);
      });
    }

    // Clear to-eval messages. If there are any duplicates we won't double-exec
    // them thanks to "text/gzip". It's more important we don't drop messages.
    vm.toEvalMessages = [];
  },
  methods: {
    resetRoom: async function() {
      let url = '/api/actions/reset-room';
      let response = await fetch(url, {
        method: 'POST',
        body: JSON.stringify({room: this.room}),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      this.messages = [];
      this.fetchMessages();

      this.resetRoomShow = false;
      this.resetRoomConfirm = "";
    },
    fetchBots: async function() {
      let url = '/api/bots?room='+this.room;
      let response = await fetch(url);
      let bots = await response.json();
      this.bots = bots;
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
      let newBot = {
        // TODO: Give these more fun GH-style names.
        name: `Bot ${this.bots.length}`,
        url: '',
        responds_to: '',
      };
      this.bots.push(newBot);
      this.submitBot(newBot);
    },
    removeBot: async function(bot) {
      if (bot.id) {
        let url = '/api/actions/bot?id='+bot.id;
        let response = await fetch(url, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        let botResult = await response.json();
      }
      await this.fetchBots();
    },
    submitBot: async function(bot, noupdate) {
      let data = {
        room: this.room,
        name: bot.name,
        url: bot.url,
        responds_to: bot.responds_to,
      };
      if (bot.id)
        data.id = bot.id;

      let url = '/api/actions/bot'
      let response = await fetch(url, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      let botResult = await response.json();

      if (!noupdate)
        await this.fetchBots();
    },
    fetchMessages: async function(options) {
      let vm = this;
      options = options || {};

      let last_id = (this.lastMessage || {}).id;
      let url = '/api/messages?room='+this.room
      if (last_id != undefined)
        url += '&since='+last_id;

      let response = await fetch(url);
      let fetchedMessages = await response.json();
      let newMessages = fetchedMessages.filter(function(newMessage) {
        // Only messages with a new ID are new messages
        return !vm.messages.some(function(message) {
          return message.id == newMessage.id;
        });
      });

      vm.toEvalMessages = newMessages;
      vm.messages = vm.messages.concat(newMessages);

      // Check if the last message contains a state which we might have to clear
      if (newMessages.length > 0) {
        let lastMessage = newMessages[newMessages.length - 1];
        this.statePresent = lastMessage.state != null;
        if (this.statePresent) {
          let bot = this.botWithId(lastMessage.reply_to);
          this.replyToBotName = bot.name || '???';
        }
      }

      if (!options.silent && this.settings.speech) {
        newMessages.forEach(function(message) {
          if (message.author != vm.settings.name)
            vm.speak(vm.markdownToText(message.text));
        });
      }
    },
    submitMessage: async function() {
      if (this.newMessage.length <= 0) {
        return;
      }
      let data = {
        room: this.room,
        author: this.settings.name,
        text: this.newMessage,
      };

      this.sendingMessage = true;

      try {
        let url = '/api/actions/message';
        let response = await fetch(url, {
          method: 'POST',
          body: JSON.stringify(data),
          headers: {
            'Content-Type': 'application/json',
          },
        });

        let messageResult = await response.json();
      } catch {}
      this.sendingMessage = false;

      this.newMessage = '';

    },
    clearState: async function() {
      let data = new FormData();
      data.append('room', this.room);

      this.sendingMessage = true;

      let url = '/api/actions/clear-room-state'
      let response = await fetch(url, {
        method: 'POST',
        body: data,
      });
      await response.json();

      this.sendingMessage = false;
    },
    autoUpdate: function() {
      let vm = this;

      vm.fetchMessages().finally(function() {
        window.setTimeout(() => vm.autoUpdate(), 2000)
      });
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
      message.showState = !message.showState;
      return message.showState;
    },
    focusMessageInput: function() {
      let vm = this;
      setTimeout(function() { vm.$el.querySelector('#message-input').focus() });
    },

    messageAlignClass: function(message) {
      // TODO: Handle messages which weren't sent by the current session.
      //       Though that might be overkill for a somewhat minor UX feature.
      return message.author == this.settings.name ? "message-right" : "message-left";
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
        this.modals.paste_conf_modal.close();
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
