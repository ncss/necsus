module Colours exposing (..)

import Style exposing (Color)

rgb : Int -> Int -> Int -> Color
rgb r g b = Style.rgb (toFloat r/255) (toFloat g/255) (toFloat b/255)

primary : Color
primary = rgb 118 181 202

backgroundSecondary : Color
backgroundSecondary = rgb 240 240 240
