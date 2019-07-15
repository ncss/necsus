module Elements exposing
  ( html
  , stylesheet
  , elements
  )

import Style exposing (StyleSheet, style)
import Style.Border as Border
import Style.Color as Color 
import Element exposing (Element, Grid, OnGrid, GridPosition, layout, grid, table, navigation, mainContent, button, text, cell)
import Element.Input as Input exposing (hiddenLabel, labelLeft)
import Element.Attributes as Attr exposing (px, fill, fillPortion, percent, content)
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
  | TabStyle
  | TabSelectedStyle
  | TabContentStyle
  | InputStyle
  | CheckboxStyle
  | MessageListStyle
  | MessageStyle
  | SettingsStyle
  | NoStyle

html : Model -> Html Msg
html model =
  layout
    stylesheet
    <| elements model

stylesheet : StyleSheet Style variation
stylesheet =
  Style.styleSheet
    [ style InputStyle
      [ Border.all 1
      , Style.prop "padding" "4px"
      ]
    , style TabSelectedStyle
      [ Color.background Colours.primary 
      ]
    ]

elements : Model -> Element Style variation Msg
elements model =
  grid PageStyle []
    { columns = [ fill ]
    , rows = [ content, fill ]
    , cells =
      [ cell
        { start = (0, 0)
        , width = 1
        , height = 1
        , content = tabs model
        }
      , cell
        { start = (0, 1)
        , width = 1
        , height = 1
        , content = tabContent model
        }
      ]
    }

tabs : Model -> Element Style variation Msg
tabs model =
  navigation NavStyle []
    { name = "Main Navigation"
    , options =
      List.map (tabButton model)
        [ ("Messages", MessagesTab)
        , ("Settings", SettingsTab)
        ]
    }

tabButton : Model -> (String, Tab) -> Element Style variation Msg
tabButton model (label, tab) =
  button (if model.tab == tab then TabSelectedStyle else TabStyle)
    [ Attr.padding 10
    , Events.onClick <| SwitchTab tab 
    ]
    <| text label 

tabContent : Model -> Element Style variation Msg
tabContent model =
  mainContent TabContentStyle
    [ Attr.padding 10 ]
    <| case model.tab of
      MessagesTab ->
        messagesTab model
      SettingsTab ->
        settingsTab model

messagesTab : Model -> Element Style variation Msg
messagesTab model =
   table NoStyle
    [ Attr.spacingXY 20 0 ]
    [ [ messagesList model
      , newMessage model
      ]
    ]

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
    , [ button NoStyle
        [ Events.onClick Listen
        ]
        <| text "listen"
      ]
    ]

settingsTab : Model -> Element Style variation Msg
settingsTab model =
  Element.table SettingsStyle []
    [ [ Input.text InputStyle []
        { onChange = UpdateUsername
        , value = model.username
        , label = labelLeft <| Element.bold "Name"
        , options = []
        } 
      , Input.text InputStyle []
        { onChange = UpdateEndpoint
        , value = model.endpoint
        , label = labelLeft <| Element.bold "Endpoint"
        , options = []
        } 
      , Input.checkbox CheckboxStyle []
        { onChange = UpdateSpeechSynthesis
        , checked = model.speechSynthesis
        , label = Element.bold "Speech Synthesis"
        , options = []
        }
      , Input.multiline InputStyle []
        { onChange = UpdateGrammar
        , value = model.grammar
        , label = labelLeft <| Element.bold "Speech Recognition Grammar"
        , options = []
        }
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
