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

type NewMessage = SubmittingMessage | NewMessage String

type alias Model =
  { tab : Tab
  , messages : RemoteMessages
  , newMessage : NewMessage 
  , username : String
  , botName : String
  , endpoint : String
  , speechSynthesis : Bool
  , grammar : String
  }

type Msg
  = SwitchTab Tab
  | LoadedRemoteMessages (Result Http.Error (List Message))
  | LoadedRemoteMessage (Result Http.Error (Message))
  | UpdateNewMessage String
  | SubmitNewMessage String
  | UpdateUsername String
  | UpdateEndpoint String
  | UpdateSpeechSynthesis Bool
  | UpdateGrammar String 
  | Listen
