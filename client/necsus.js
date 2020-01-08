let plainTextRenderer = new PlainTextRenderer;

let app = new Vue({
  el: '#necsus',
  data: {
    room: '',
    settings: {
      open: false,
      name: 'Anonymous',
      speech: true,
      resetRoom: false,
      bots: [],
    },
    messages: [],
    newMessage: '',
    sendingMessage: false,
  },
  created: function() {
    let vm = this;

    /*
      Determine the room
    */
    vm.room = window.location.pathname.slice(1);

    /*
      Fetch the room's messages and settings 
    */
    vm.fetchBots();
    vm.fetchMessages({silent: true});
    // Initially scroll to the bottom of the message list
    this.$nextTick(function() {
      this.scrollToBottomOfMessages();
    });

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
  updated: function() {
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

      this.settings.resetRoom = false;
    },
    fetchBots: async function() {
      let url = '/api/bots?room='+this.room;
      let response = await fetch(url);
      let bots = await response.json();
      this.settings.bots = bots;
    },
    addBot: function() {
      this.settings.bots.push({
        name: '',
        url: '',
        responds_to: '',
      });
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
    submitBot: async function(bot) {
      let data = {
        room: this.room,
        name: bot.name,
        url: bot.url,
        responds_to: bot.responds_to,
      };
      if (bot.id) {
        data.id = bot.id;
      }

      let url = '/api/actions/bot'
      let response = await fetch(url, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      let botResult = await response.json();

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

      vm.messages = vm.messages.concat(newMessages);

      // Move to new messages if there are any
      if (newMessages.length > 0) {
        this.$nextTick(function() {
          this.scrollToBottomOfMessages();
        });
      }

      if (!options.silent) {
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

      let url = '/api/actions/message';
      let response = await fetch(url, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      let messageResult = await response.json();

      this.sendingMessage = false;

      this.newMessage = '';
    },
    autoUpdate: function() {
      let vm = this;
      if (vm.autoUpdater) window.clearInterval();
      vm.autoUpdater = window.setInterval(function() {
        vm.fetchMessages();
      }, 1500);
    },
    speak: function(text) {
      if (window.SpeechSynthesisUtterance) {
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
    scrollToBottomOfMessages: function() {
      let spacer = this.$el.querySelector('#messages-spacer');
      let messagesContainer = this.$el.querySelector('#messages');
      let messagesList = this.$el.querySelector('#messages-list');
      let newMessage = this.$el.querySelector('#new-message');
      let header = this.$el.querySelector('header');
      let messages = [...this.$el.querySelectorAll('.message')];

      let messagesTop, messagesBottom;
      if (messages[0]) {
        messagesTop = messages[0].getBoundingClientRect().top;
        messagesBottom = messages[messages.length-1].getBoundingClientRect().bottom;
      } else {
        messagesTop = 0;
        messagesBottom = 0;
      }
      let messagesHeight = window.innerHeight - header.getBoundingClientRect().height - newMessage.getBoundingClientRect().height;
      let visibleMessagesHeight = messagesBottom - messagesTop;
      let allMessagesHeight = messagesList.scrollHeight;

      spacer.style.height = Math.max(messagesHeight - visibleMessagesHeight, 0) + 'px';
      messagesList.scrollTo(0, allMessagesHeight);
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
  },
  computed: {
    lastMessage: function() {
      if (this.messages.length > 0) {
        return this.messages[this.messages.length-1];
      } else {
        return undefined;
      };
    },
  },
});
