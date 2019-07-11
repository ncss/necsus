import Browser exposing (Document)

import Html exposing (Html)
import Html.Attributes as Attr
import Html.Events exposing (on, onInput)

import Http
import Json.Decode as D exposing (Decoder)
import Json.Encode as E exposing (Value)

import Model exposing (..)
import Elements

main =
  Browser.document
  { init = init
  , update = update
  , view = view
  , subscriptions = subscriptions 
  }

init : () -> (Model, Cmd Msg)
init flags =
  (initModel, getMessages)

initModel : Model
initModel =
  { tab = MessagesTab
  , messages = Loading
  , newMessage = NewMessage ""
  , endpoint = ""
  }

update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
  case msg of
    SwitchTab tab ->
      ({ model | tab = tab }, Cmd.none)
    LoadedRemoteMessages (Ok messages) ->
      ({ model | messages = Messages messages }, Cmd.none)
    LoadedRemoteMessages (Err error) ->
      ({ model | messages = Error "something went bad" }, Cmd.none)
    LoadedRemoteMessage (Ok message) ->
      case model.messages of
        Messages messages ->
          ({ model | messages = Messages <| messages++[message] }, Cmd.none)
        _ ->
          ({ model | messages = Messages [message] }, Cmd.none)
    LoadedRemoteMessage (Err error) ->
      ({ model | messages = Error "something went bad" }, Cmd.none)
    UpdateNewMessage message ->
      ({ model | newMessage =
        case model.newMessage of
          SubmittingMessage ->
            NewMessage ""
          NewMessage oldMessage ->
            NewMessage message
       }, Cmd.none)
    SubmitNewMessage message ->
      ({ model | newMessage = SubmittingMessage },
        if String.startsWith "/" message then
          let
            commandRaw = String.words message
            command = commandRaw
              |> List.head
              |> Maybe.withDefault ""
              |> String.dropLeft 1
            content = commandRaw
              |> List.drop 1
              |> String.join " "
          in
            postCommand { author = "kenni", command = command, text = content, endpoint = model.endpoint }
        else
          postMessage { author = "kenni", text = message }
      )
    UpdateEndpoint endpoint ->
      ({ model | endpoint = endpoint }, Cmd.none)

subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.none

view : Model -> Document Msg
view model =
  { title = "NeCCSus"
  , body = [ Elements.html model ]
  }

getMessages : Cmd Msg
getMessages =
  Http.get
    { url = "/api/actions/message"
    , expect = Http.expectJson LoadedRemoteMessages decodeMessages
    }

postMessage : Message -> Cmd Msg
postMessage message =
  Http.post
    { url = "/api/actions/message"
    , body = messageBody message
    , expect = Http.expectJson LoadedRemoteMessage decodeMessage
    }

postCommand : Command -> Cmd Msg
postCommand command =
  Http.post
    { url = "/api/actions/command"
    , body = commandBody command
    , expect = Http.expectJson LoadedRemoteMessage decodeMessage
    }

decodeMessages : Decoder (List Message)
decodeMessages =
  D.list decodeMessage

decodeMessage : Decoder Message
decodeMessage =
  D.map2 Message
    (D.field "author" D.string)
    (D.field "text" D.string)

messageBody : Message -> Http.Body
messageBody message =
  Http.multipartBody
    [ Http.stringPart "author" message.author
    , Http.stringPart "text" message.text
    ]

commandBody : Command -> Http.Body
commandBody command =
  Http.multipartBody
    [ Http.stringPart "author" command.author
    , Http.stringPart "command" command.command
    , Http.stringPart "text" command.text
    , Http.stringPart "endpoint" command.endpoint
    ]
