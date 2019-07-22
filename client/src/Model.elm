module Model exposing (..)

import Http

type Tab
  = MessagesTab
  | SettingsTab

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

type MessageType
  = TextMessage
  | CommandMessage BotSettings

type alias Model =
  { tab : Tab
  , messages : RemoteMessages
  , newMessage : String
  , settings : Settings
  }

type alias Settings =
  { username : String
  , speechSynthesis : Bool
  , botSettings : List BotSettings
  }

type Msg
  = SwitchTab Tab
  | LoadedRemoteMessages (Result Http.Error (List Message))
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

type BotSettingMsg
  = UpdateBotName String
  | UpdateEndpoint String
