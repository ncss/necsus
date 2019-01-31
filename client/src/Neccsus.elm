import Browser exposing (Document)
import Html exposing (Html)

import Http
import Json.Decode as D exposing (Decoder)

type Model = Loading | Messages (List Message) | Error String
type alias Message =
  { author : String
  , text : String
  }

type Msg =
  LoadedMessages (Result Http.Error (List Message))

main =
  Browser.document
  { init = init
  , update = update
  , view = view
  , subscriptions = subscriptions 
  }

init : () -> (Model, Cmd Msg)
init flags =
  (Loading, getMessages)

update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
  case msg of
    LoadedMessages (Ok messages) ->
      (Messages messages, Cmd.none)
    LoadedMessages (Err error) ->
      (Error "something went bad", Cmd.none)

subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.none

view : Model -> Document Msg
view model =
  { title = "NeCCSus"
  , body =
    [ case model of
      Loading ->
        Html.text "Loading messages"
      Error message ->
        Html.text message
      Messages messages ->
        Html.ol []
          <| List.map ((\message -> Html.li [] [ message ]) << viewMessage) messages
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
    { url = "http://localhost:5005/api/actions/message"
    , expect = Http.expectJson LoadedMessages decodeMessages
    }

decodeMessages : Decoder (List Message)
decodeMessages =
  D.list decodeMessage

decodeMessage : Decoder Message
decodeMessage =
  D.map2 Message
    (D.field "author" D.string)
    (D.field "text" D.string)
