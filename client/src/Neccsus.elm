import Browser exposing (Document)

import Html exposing (Html)
import Html.Attributes as Attr
import Html.Events exposing (on)

import Http
import Json.Decode as D exposing (Decoder)
import Json.Encode as E exposing (Value)

type alias Model =
  { messages : RemoteMessages
  , newMessage : String
  }

type RemoteMessages = Loading | Messages (List Message) | Error String

type alias Message =
  { author : String
  , text : String
  }

type alias Command =
  { author : String
  , command : String
  , text : String
  }

type Msg
  = LoadedRemoteMessages (Result Http.Error (List Message))
  | LoadedRemoteMessage (Result Http.Error (Message))
  | UpdateNewMessage String
  | SubmitNewMessage String

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
  { messages = Loading
  , newMessage = ""
  }

update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
  case msg of
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
      ({ model | newMessage = message }, Cmd.none)
    SubmitNewMessage message ->
      ({ model | newMessage = "" },
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
            postCommand { author = "kenni", command = command, text = content }
        else
          postMessage { author = "kenni", text = message }
      )

subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.none

view : Model -> Document Msg
view model =
  { title = "NeCCSus"
  , body =
    [ case model.messages of
      Loading ->
        Html.text "Loading messages"
      Error message ->
        Html.text message
      Messages messages ->
        Html.ol []
          <| List.map ((\message -> Html.li [] [ message ]) << viewMessage) messages
    , Html.input
      [ Attr.placeholder "Type your message here"
      , Attr.value model.newMessage
      , onKeyPress UpdateNewMessage
      , onEnterKey SubmitNewMessage
      ]
      []
    ]
  }

viewMessage : Message -> Html Msg
viewMessage message =
  Html.div []
    [ Html.h4 [] [ Html.text message.author ]
    , Html.div [] [ Html.text message.text ]
    ]

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
    ]

onKeyPress : (String -> Msg) -> Html.Attribute Msg
onKeyPress func =
  on "keypress"
    <| D.map func decodeValue

onEnterKey : (String -> Msg) -> Html.Attribute Msg
onEnterKey func =
  on "keypress"
    <| D.map func decodeValueOnEnter
  
decodeValueOnEnter : Decoder String
decodeValueOnEnter =
  D.map2 Tuple.pair
    decodeKey
    decodeValue
  |> D.andThen
    (\(key, value) ->
      case key of
        "Enter" -> D.succeed value
        _ -> D.fail "ignoring keyboard event"
    )

decodeKey : Decoder String
decodeKey =
  D.field "key" D.string

decodeValue : Decoder String
decodeValue =
  D.at ["target", "value"] D.string

traceDecoder : String -> Decoder msg -> Decoder msg
traceDecoder message decoder =
    D.value
    |> D.andThen
      (\value ->
        case D.decodeValue decoder value of
          Ok decoded ->
            D.succeed decoded
          Err err ->
            D.fail <| Debug.log message <| D.errorToString err
      )
