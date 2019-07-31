module Elements exposing
  ( html
  , stylesheet
  , elements
  )

import Style exposing (StyleSheet, style)
import Style.Border as Border
import Style.Color as Color 
import Style.Font as Font
import Style.Scale as Scale
import Element exposing (Element, Grid, OnGrid, GridPosition, viewport, grid, table, navigation, mainContent, button, text, cell, empty)
import Element.Input as Input exposing (hiddenLabel, labelLeft)
import Element.Attributes as Attr exposing (width, height, px, fill, fillPortion, percent, content)
import Element.Events as Events

import Html exposing (Html)
import Html.Attributes exposing (value)
import Html.Events exposing (on)

import Json.Decode as D exposing (Decoder)

import Model exposing (..)
import Colours

type Style
  = PageStyle 
  | NavStyle
  | ModalStyle
  | InputStyle
  | ButtonStyle
  | CheckboxStyle
  | MessageListStyle
  | MessageStyle
  | SettingsStyle
  | BotSettingsStyle
  | HeadingStyle
  | SubHeadingStyle
  | NoStyle

html : Model -> Html Msg
html model =
  viewport
    stylesheet
    <| elements model

stylesheet : StyleSheet Style variation
stylesheet =
  Style.styleSheet
    [ style InputStyle
      [ Border.all 1
      , Style.prop "padding" "4px"
      ]
    , style ButtonStyle
      [ Color.background Colours.primary 
      , Border.rounded 5
      , Style.prop "padding" "8px"
      ]
    , style SettingsStyle
      [ Color.background Colours.backgroundPrimary
      ]
    , style BotSettingsStyle
      [ Color.background Colours.backgroundSecondary 
      ]
    , style HeadingStyle
      [ Font.size (scaled 3)
      ]
    , style SubHeadingStyle
      [ Font.size (scaled 2)
      ]
    ]

scaled =
  Scale.modular 16 1.618

elements : Model -> Element Style variation Msg
elements model =
  grid PageStyle
    [ height fill
    ]
    { columns = [ fill, content ]
    , rows = [ content, fill, content ]
    , cells =
      [ cell
        { start = (1, 0)
        , width = 1
        , height = 1
        , content = settingsButton model
        }
      , cell
        { start = (0, 0)
        , width = 1
        , height = 1
        , content = if model.settings.show then settingsModal model else empty
        }
      , cell
        { start = (0, 1)
        , width = 2
        , height = 1
        , content = messagesList model
        }
      , cell
        { start = (0, 2)
        , width = 2
        , height = 1
        , content = newMessage model
        }
      ]
    }

messagesList : Model -> Element Style variation Msg
messagesList model =
  table MessageListStyle
    [ Attr.spacingXY 20 0 ]
    [ case model.messages of
      Loading ->
        [ text "Loading"]
      Messages messages ->
        messages |> List.map messageElement
      Error error ->
        [ text error ]
   ]

messageElement : Message -> Element Style variation Msg
messageElement message =
  table MessageStyle
    [ Attr.spacingXY 4 0 ]
    [ [ Element.bold message.author
      , text message.text
      ]
    ]

newMessage : Model -> Element Style variation Msg
newMessage model =
  Element.table NoStyle []
    [ [ Element.html <| Html.textarea
        [ on "keyup"
          <| decodeValueOnKey
          <| \key shift text ->
            case (key, shift) of
              ("Enter", False) ->
                SubmitNewMessage text
              _ ->
                UpdateNewMessage text
        , value model.newMessage
        ]
        [
        ]
      ]
    , [ button ButtonStyle
        [ Events.onClick Listen
        ]
        <| text "listen"
      ]
    ]

settingsButton : Model -> Element Style variation Msg
settingsButton model =
  Element.button ButtonStyle
    [ Events.onClick <| ShowSettings <| not model.settings.show
    ]
    <| text "Settings"

settingsModal : Model -> Element Style variation Msg
settingsModal model =
  Element.modal ModalStyle
    [ Attr.center
    , Attr.spacingXY 0 50
    , width <| percent 80
    , height content
    ]
    <| settingsContent model

settingsContent : Model -> Element Style variation Msg
settingsContent model =
  Element.table SettingsStyle
    [ Attr.spacingXY 10 0
    , Attr.paddingXY 10 10
    ]
    [ [ Element.h1 HeadingStyle []
        <| text "Settings"
      , Element.h2 SubHeadingStyle []
        <| text "Main"
      , Input.text InputStyle []
        { onChange = UpdateUsername
        , value = model.settings.username
        , label = labelLeft <| Element.bold "Name"
        , options = []
        } 
      , Input.checkbox CheckboxStyle []
        { onChange = UpdateSpeechSynthesis
        , checked = model.settings.speechSynthesis
        , label = Element.bold "Speech Synthesis"
        , options = []
        }
      , Element.h2 SubHeadingStyle []
        <| text "Bots"
      ]
      ++
      (List.indexedMap botSettings model.settings.botSettings)
      ++
      [ button ButtonStyle
        [ Events.onClick AddBot
        ]
        <| text "Add bot"
      ]
    ]

botSettings : Int -> BotSettings -> Element Style variation Msg
botSettings index settings =
  Element.table BotSettingsStyle
    [ Attr.spacingXY 10 0
    , Attr.paddingXY 10 10
    ]
    [ [ Input.text InputStyle []
        { onChange = UpdateBotSettings index << UpdateBotName
        , value = settings.name
        , label = labelLeft <| Element.bold "Bot Name"
        , options = []
        }
      , Input.text InputStyle []
        { onChange = UpdateBotSettings index << UpdateEndpoint
        , value = settings.endpoint
        , label = labelLeft <| Element.bold "Endpoint"
        , options = []
        } 
      , button ButtonStyle
        [ Events.onClick (RemoveBot index) 
        ]
        <| text "Remove bot"
      ]
    ]

decodeValueOnKey : (String -> Bool -> String -> msg) -> Decoder msg 
decodeValueOnKey func =
  D.map3 func
    decodeKey
    decodeShift
    decodeValue

decodeShift : Decoder Bool 
decodeShift =
  D.field "shiftKey" D.bool

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
