let app = new Vue({
  el: '#necsus',
  data: {
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
  },
  created: function() {
    this.refreshWelcome();
  },
  methods: {
    refreshWelcome: function() {
      let vm = this;
      vm.welcome = vm.randomChoice(vm.possibleWelcomes);
      window.setTimeout(() => vm.refreshWelcome(), 5000)
    },
    randomChoice: function(array) {
      return array[Math.floor(Math.random() * array.length)];
    },
    joinRoom: function() {
      if (this.room_name !== "") {
        window.location = window.location.origin + `/${this.room_name}`;
      }
    },
  },
});
