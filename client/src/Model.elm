module Model exposing (..)

import Http

type alias Message =
  { author : String
  , text : String
  }

type alias Command =
  { author : String
  , command : String
  , text : String
  , endpoint : String
  }

type SpeechResult = InterimSpeechResult String | FinalSpeechResult String

type RemoteMessages = Loading | Messages (List Message) | Error String

type alias BotSettings =
  { name : String
  , endpoint : String
  }

type alias Settings =
  { username : String
  , speechSynthesis : Bool
  , botSettings : List BotSettings
  , show : Bool
  }

type alias Model =
  { messages : RemoteMessages
  , newMessage : String
  , settings : Settings
  }

type MessageType
  = TextMessage
  | CommandMessage BotSettings

type Msg
  = LoadedRemoteMessages (Result Http.Error (List Message))
  | LoadedRemoteMessage (Result Http.Error (Message))
  | UpdateNewMessage String
  | SubmitNewMessage String
  | Listen
  | UpdateSettings Settings
  | UpdateUsername String
  | UpdateSpeechSynthesis Bool
  | AddBot
  | RemoveBot Int 
  | UpdateBotSettings Int BotSettingMsg
  | ShowSettings Bool

type BotSettingMsg
  = UpdateBotName String
  | UpdateEndpoint String
