const { createApp, ref } = Vue

const app = createApp({
  data: () => ({
    room_name: '',
    welcome: undefined,
    possibleWelcomes: [
      "G'day",
      "Welcome",
      "Dobrodošli",
      "Добродошли",
      "Добро пожаловать",
      "Bienvenue",
      "Bienvenido",
      "Willkommen",
      "ようこそ",
      "欢迎光临",
      "Selamat datang",
      "Yarrr",
      "Ahoy",
      "Arrr me hearties, yo-ho",
    ],
  }),
  // Changed from created to mounted because the DOM isn't ready yet in created throwing an error
  mounted: function() {
    this.refreshWelcome();
  },
  methods: {
    refreshWelcome: function() {
      let vm = this;
      vm.welcome = vm.randomChoice(vm.possibleWelcomes);
      vm.typeSentence(vm.welcome, "lobby-welcome-text");
      window.setTimeout(() => vm.refreshWelcome(), 5000)
    },
    typeSentence: function (text, elementId) {
      const element = document.getElementById(elementId);
      const oldElementLength = element.children.length;
      
      // untype any existing text
      for (let i = oldElementLength - 1; i >= 0; i--) {
        setTimeout(() => {
          element.removeChild(element.children[i]);
        }, 100 * (element.children.length - i));
      } 

      // we are excited!
      const letters = [...text.split(""), '!']; 
      
      // type forwards the new text
      for (let i = 0; i < letters.length; i++) {
        setTimeout(() => {
          const element = document.createElement("span");
          element.className = "letter";
          element.innerHTML = letters[i];
          document.getElementById(elementId).appendChild(element);
          
          // we need to wait for the old element to be removed
          // before we can start the adding animation
        }, oldElementLength * 100 + 100 * i);
      }

    },
    randomChoice: function(array) {
      return array[Math.floor(Math.random() * array.length)];
    },
    joinRoom: function() {
      if (this.room_name !== "") {
        let safe_room = encodeURIComponent(this.room_name);
        window.location = window.location.origin + `/${safe_room}`;
      }
    },
  },
}).mount('#necsus');