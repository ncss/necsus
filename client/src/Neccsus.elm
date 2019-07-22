port module Neccsus exposing (..)

import Browser exposing (Document)

import Html exposing (Html)
import Html.Attributes as Attr
import Html.Events exposing (on, onInput)

import Http
import Json.Decode as D exposing (Decoder)
import Json.Encode as E exposing (Value)

import List.Extra as List

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
  , settings = initSettings
  }

initSettings : Settings
initSettings =
  { username = "user"
  , speechSynthesis = False
  , botSettings = [ initBotSettings ]
  }

initBotSettings : BotSettings
initBotSettings =
  { name = "echo"
  , endpoint = "https://flask-endpoint-echo--kennib.repl.co"
  }

port cache : Value -> Cmd msg
port uncache : (Value -> msg) -> Sub msg

cacheEncoder : Settings -> Value
cacheEncoder settings =
  E.object
    [ ("username", E.string settings.username)
    , ("speechSynthesis", E.bool settings.speechSynthesis)
    , ("botSettings", E.list botSettingsEncoder settings.botSettings)
    ]

botSettingsEncoder : BotSettings -> Value
botSettingsEncoder botSettings =
  E.object
    [ ("name", E.string botSettings.name)
    , ("endpoint", E.string botSettings.endpoint)
    ]

cacheDecoder : Decoder Settings
cacheDecoder =
  D.map3 Settings 
    (D.field "username" D.string)
    (D.field "speechSynthesis" D.bool)
    (D.field "botSettings" <| D.list botSettingsDecoder)

botSettingsDecoder : Decoder BotSettings
botSettingsDecoder =
  D.map2 BotSettings
    (D.field "name" D.string)
    (D.field "endpoint" D.string)

port speak : String -> Cmd msg

port listen : () -> Cmd msg
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
          , if model.settings.speechSynthesis && message.author /= model.settings.username then
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
        case messageType model message of
          CommandMessage botSettings ->
            Cmd.batch
              [ postMessage { author = model.settings.username, text = message }
              , postCommand { author = model.settings.username, command = botSettings.name, text = message, endpoint = botSettings.endpoint }
              ]
          TextMessage ->
            postMessage { author = model.settings.username, text = message }
      )
    Listen ->
      (model, listen ())
    UpdateSettings settings ->
      updateSettings model <| \_ -> settings
    UpdateUsername username ->
      updateSettings model <| \settings -> { settings | username = username }
    UpdateSpeechSynthesis speechSynthesis ->
      updateSettings model <| \settings -> { settings | speechSynthesis = speechSynthesis }
    AddBot ->
      updateSettings model <| \settings -> { settings | botSettings = settings.botSettings ++ [initBotSettings] }
    RemoveBot index ->
      updateSettings model <| \settings -> { settings | botSettings = List.removeAt index settings.botSettings }
    UpdateBotSettings botIndex botSettingMsg ->
      updateBotSettings botIndex botSettingMsg model

updateSettings : Model -> (Settings -> Settings) -> (Model, Cmd Msg)
updateSettings model updates =
  let
    newSettings = updates model.settings 
  in
    ({ model | settings = newSettings}, cache <| cacheEncoder newSettings)

updateBotSettings : Int -> BotSettingMsg -> Model -> (Model, Cmd Msg)
updateBotSettings botIndex msg model =
  let
    maybeBotSettings = List.getAt botIndex model.settings.botSettings
    updateBot updates =
      case maybeBotSettings of
        Just botSettings ->
          updateSettings model <| \settings -> { settings | botSettings = List.setAt botIndex (updates botSettings) settings.botSettings }
        Nothing ->
          (model, Cmd.none)
  in
    case msg of
      UpdateBotName name ->
        updateBot <| \bot -> { bot | name = name }
      UpdateEndpoint endpoint ->
        updateBot <| \bot -> { bot | endpoint = endpoint }

messageType : Model -> String -> MessageType
messageType model message =
  let
    botCommand = List.find isCommand model.settings.botSettings
    isCommand bot = String.contains (String.toLower bot.name) (String.toLower message)
  in
    case botCommand of
      Just botSettings ->
        CommandMessage botSettings
      Nothing ->
        TextMessage

subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.batch
    [ uncache
      <| D.decodeValue cacheDecoder
        >> Result.withDefault initSettings
        >> UpdateSettings
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
