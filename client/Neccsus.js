var app = new Vue({
  el: '#neccsus',
  data: {
    room: 'Group 1',
    settings: {
      open: true,
      name: 'Kenni',
      speech: true,
      bots: [{
        name: 'Echo',
        url: 'https://flask.repl.co'
      }, {
        name: 'Echo',
        url: 'https://flask.repl.co'
      }],
    },
    messages: [
      { author: 'Kenni', text: 'Hello Vue!' },
      { author: 'Kenni', text: 'Hello Vue!' },
      { author: 'Kenni', text: 'Hello Vue!' },
      { author: 'Kenni', text: 'Hello Vue!' },
      { author: 'Kenni', text: 'Hello Vue!' },
    ],
    newMessage: '',
  },
  mounted: function() {
    var vm = this;

    /*
      Scroll to bottom of messages
    */
    vm.scrollToBottomOfMessages();

    /*
      Speech recognition
    */
    var recognition = new webkitSpeechRecognition();
    vm.speechRecognition = recognition;

    recognition.lang = 'en-AU';
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function(event) {
      var firstResult = event.results[0];
      var firstAlternative = firstResult[0];

      vm.speechRecognitionResult({
        result: firstAlternative.transcript,
        isFinal: firstResult.isFinal,
      });
    };
  },
  methods: {
    scrollToBottomOfMessages: function() {
      var spacer = this.$el.querySelector('#messages-spacer');
      var messagesContainer = this.$el.querySelector('#messages');
      var messagesList = this.$el.querySelector('#messages-list');
      var messages = [...this.$el.querySelectorAll('.message')];

      var messagesHeight = messages[messages.length-1].getBoundingClientRect().bottom - messages[0].getBoundingClientRect().top;
      spacer.style.height = (messagesContainer.scrollHeight - messagesHeight - 30) + 'px';
      messagesList.scrollTo(0, messagesContainer.scrollHeight);
    },
    rows: function() {
      return this.newMessage.split(/\r\n|\r|\n/).length;
    },
    speak: function(text) {
      var utterance = new SpeechSynthesisUtterance(text);
      speechSynthesis.speak(utterance);
    },
    listen: function() {
      this.speechRecognition.start()
    },
    speechRecognitionResult: function(speech) {
      this.newMessage = speech.result;
    },
  },
});
