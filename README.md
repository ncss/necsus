# NeCSuS

[NeCSuS](https://chat.ncss.cloud) is a chat app which makes it simple to connect "bots" (i.e., simple HTTP servers that reply to messages).
NeCSuS has the ability to host chats in "rooms", listen to voice commands and speak chat messages out loud.


## API

Documentation on the API can be found on [the main NeCSuS server](https://chat.ncss.cloud/docs) or at `/docs` on your local instance.


## FAQ

### What is NeCSuS?
An web app for chat.

### How do I post (images|links|formatted text)?
The client uses [markedjs](https://github.com/markedjs/marked) to render the text.
This means you need to use plain text to post any content.
Look at the [demo page](https://marked.js.org/demo/?text=%23%20Nutrition%0A!%5BNutella%5D(https%3A%2F%2Fstatic.openfoodfacts.org%2Fimages%2Fproducts%2F301%2F762%2F042%2F9484%2Ffront_fr.219.200.jpg)%0A%0A%23%23%20Nutella%0A%0A%5BNutella%5D(https%3A%2F%2Fau.openfoodfacts.org%2Fproduct%2F3017620429484%2Fnutella)%20is%20**not**%20healthy&options=&version=master) to see examples of the plain text used to post (images|links|formatted text).
