port module Neccsus exposing (..)

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
  , newMessage = ""
  , username = "user"
  , botName = "bot"
  , endpoint = ""
  , speechSynthesis = False
  , grammar = "#JSGF V1.0; grammar confirmation; public <confirmation> = yes | no ;"
  }

port cache : Value -> Cmd msg
port uncache : (Value -> msg) -> Sub msg

cacheEncoder : String -> Value
cacheEncoder endpoint = E.string endpoint

cacheDecoder : Decoder (Maybe String)
cacheDecoder = D.nullable D.string

port speak : String -> Cmd msg

port listen : String -> Cmd msg
port speechResult : (Value -> msg) -> Sub msg

speechResultDecoder : Decoder SpeechResult
speechResultDecoder =
  let
    result text isFinal =
      if isFinal then
        FinalSpeechResult text 
      else
        InterimSpeechResult text 
  in
    D.map2 result
      (D.field "result" D.string)
      (D.field "isFinal" D.bool)

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
          ( { model | messages = Messages <| messages++[message] }
          , if model.speechSynthesis && message.author /= model.username then
              speak message.text
            else
              Cmd.none
          )
        _ ->
          ({ model | messages = Messages [message] }, Cmd.none)
    LoadedRemoteMessage (Err error) ->
      ({ model | messages = Error "something went bad" }, Cmd.none)
    UpdateNewMessage message ->
      ({ model | newMessage = message }, Cmd.none)
    SubmitNewMessage message ->
      ({ model | newMessage = "" },
        if String.contains model.botName message then
          Cmd.batch
            [ postMessage { author = model.username, text = message }
            , postCommand { author = model.username, command = model.botName, text = message, endpoint = model.endpoint }
            ]
        else
          postMessage { author = model.username, text = message }
      )
    UpdateUsername username ->
      ({ model | username = username }, Cmd.none)
    UpdateEndpoint endpoint ->
      ({ model | endpoint = endpoint }, cache <| cacheEncoder endpoint)
    UpdateSpeechSynthesis value ->
      ({ model | speechSynthesis = value }, Cmd.none)
    UpdateGrammar grammar ->
      ({ model | grammar = grammar }, Cmd.none)
    Listen ->
      (model, listen model.grammar)

subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.batch
    [ uncache
      <| D.decodeValue cacheDecoder
        >> Result.withDefault (Nothing)
        >> Maybe.withDefault ""
        >> UpdateEndpoint
    , speechResult
      <| D.decodeValue speechResultDecoder
        >> Result.withDefault (InterimSpeechResult "")
        >> (\result -> case result of
            InterimSpeechResult text -> UpdateNewMessage text
            FinalSpeechResult text -> SubmitNewMessage text
          )
    ]

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
