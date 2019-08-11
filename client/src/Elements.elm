module Elements exposing
  ( html
  , elements
  )

import Element exposing (Element, Attribute, row, column, el, text, none, width, height, px, fill, fillPortion, centerX, padding, paddingXY, paddingEach, spacing, spacingXY, inFront, behindContent, alignTop, alignBottom, alignRight)
import Element.Input as Input exposing (button, labelLeft, labelHidden)
import Element.Events as Events
import Element.Font as Font
import Element.Background as Background
import Element.Region as Region

import Html exposing (Html)
import Html.Attributes exposing (attribute, value)
import Html.Events exposing (on)

import Json.Decode as D exposing (Decoder)

import Model exposing (..)
import Colours

html : Model -> Html Msg
html model =
  Element.layout
    []
    <| elements model

scaled =
  Element.modular 16 1.25

elements : Model -> Element Msg
elements model =
 column 
    [ height fill
    , width fill
    , inFront <| if model.settings.show then modal (ShowSettings False) <| settingsContent model else none 
    ]
    [ el
      [ alignRight
      ]
      <| settingsButton model
    , messagesList model
    , newMessage model
    ]

messagesList : Model -> Element Msg
messagesList model =
  column
    [ height fill
    , spacing 20
    , padding 20
    ]
    <| case model.messages of
      Loading ->
        [ text "Loading" ]
      Messages messages ->
        messages |> List.map messageElement
      Error error ->
        [ text error ]

messageElement : Message -> Element Msg
messageElement message =
  column
    [ spacing 5
    , alignBottom
    ]
    [ bold message.author
    , text message.text
    ]

newMessage : Model -> Element Msg
newMessage model =
  row
    [ width fill
    , padding 20
    ]
    [ el
      [ width fill
      ]
      <| newMessageInput model 
    , button
      (alignRight::buttonStyle)
      { onPress = Just Listen
      , label = text "listen"
      }
    ]

newMessageInput : Model -> Element Msg
newMessageInput model =
  Element.html <| Html.textarea
    [ on "keyup"
      <| decodeValueOnKey
      <| \key shift text ->
        case (key, shift) of
          ("Enter", False) ->
            SubmitNewMessage text
          _ ->
            UpdateNewMessage text
    , value model.newMessage
    , attribute "rows" <| String.fromInt <| max 2 <| List.length <| String.lines <| model.newMessage
    ]
    []

settingsButton : Model -> Element Msg
settingsButton model =
  button
    [ padding 5 
    , Background.color Colours.primary
    ]
    { onPress = Just <| ShowSettings <| not model.settings.show
    , label = text "Settings"
    }

settingsContent : Model -> Element Msg
settingsContent model =
  column
    [ spacing 10
    , padding 10
    , Background.color Colours.backgroundPrimary
    ]
    <|
      [ el
        (heading 2)
        <| text "Settings"
      , settingsSection "Main"
        [ Input.text []
          { onChange = UpdateUsername
          , text = model.settings.username
          , placeholder = Nothing
          , label = labelLeft [] <| bold "Name"
          } 
        , Input.checkbox []
          { onChange = UpdateSpeechSynthesis
          , icon = Input.defaultCheckbox
          , checked = model.settings.speechSynthesis
          , label = labelLeft [] <| bold "Speech Synthesis"
          }
        ]
      , settingsSection "Bots"
          <|
            (List.indexedMap botSettings model.settings.botSettings)
            ++
            [ button
              ( buttonStyle ++ [ width fill, Font.center ] )
              { onPress = Just AddBot
              , label = text "Add bot"
              }
            ]
      , button
        buttonStyle
        { onPress = Just <| ShowSettings False
        , label = text "Save"
        }
      ]

settingsSection : String -> List (Element Msg) -> Element Msg
settingsSection title content =
  column
    [ spacing 10
    , padding 10
    ]
    <|
      [ el
        (heading 3)
        <| text title
      ]
      ++
      content 


botSettings : Int -> BotSettings -> Element Msg
botSettings index settings =
  Element.column
    [ spacing 10
    , padding 10
    , Background.color Colours.backgroundSecondary
    ]
    [ Input.text []
      { onChange = UpdateBotSettings index << UpdateBotName
      , text = settings.name
      , placeholder = Nothing
      , label = labelLeft [] <| bold "Bot Name"
      }
    , Input.text []
      { onChange = UpdateBotSettings index << UpdateEndpoint
      , text = settings.endpoint
      , placeholder = Nothing
      , label = labelLeft [] <| bold "Endpoint"
      } 
    , button
      buttonStyle
      { onPress = Just <| RemoveBot index
      , label = text "Remove bot"
      }
    ]

heading : Int -> List (Attribute msg)
heading order =
  [ Region.heading order
  , paddingEach { top = 20, bottom = 5, left = 0, right = 0 }
  , Font.size <| round <| scaled (6-order)
  ]

modal : msg -> Element msg -> Element msg
modal close content =
  el
    [ width fill
    , height fill
    , padding 20
    , behindContent <| el
      [ width fill
      , height fill
      , Events.onClick close 
      , Background.color Colours.backgroundOverlay
      ]
      none
    ]
    <| el
      [ centerX
      , Background.color Colours.backgroundPrimary
      , inFront <| el
        [ alignTop
        , alignRight
        , padding 5
        , Events.onClick close
        ]
        <| text "X"
      ]
      content 

buttonStyle : List (Attribute msg)
buttonStyle =
  [ padding 5 
  , Background.color Colours.primary
  ]

bold : String -> Element msg
bold string =
  el
    [ Font.bold
    ]
    <| text string

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
