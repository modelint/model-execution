scenario : One Bank No Stops
--
Bank
Name | Passenger load time | Block clear time | Max close attempts | Average cabin speed | Average stop duration
--
L { [Lower Floors]     [4.0] [2.0] [25] [7.0] [9.0] }
--
Cabin
Shaft | Travel direction | Current floor
--
{ [S1] [up]   [L]  } > PICKUP DROPOFF
{ [S2] [down] [3] } > PICKUP DROPOFF
--
Door
Shaft | Close attempts | Lock requested | Held | Blocked | Emergency hold
--
{ [S1] [0] [False] [False] [False] [False] } > CLOSED
{ [S2] [0] [False] [False] [False] [False] } > CLOSED
--
Shaft
ID | In service | R1>Bank
--
{ [S1] [True] @L } R53> NO TRANSFER > IDLE
{ [S2] [True] @L } R53> NO TRANSFER > IDLE
--
Floor
Name | Height
--
{ [5]  [22.4] }
{ [4]  [19.2] }
{ [3]  [16.0] }
{ [2]  [12.8] }
{ [1]  [9.6] }
{ [L]  [6.4] }
--
Bank Level
Bank | Floor
--
LF5  { [Lower Floors] [5] }
LF4  { [Lower Floors] [4] }
LF3  { [Lower Floors] [3] }
LF2  { [Lower Floors] [2] }
LF1  { [Lower Floors] [1] }
LFL  { [Lower Floors] [L] }
--
Top Bank Level
R38>Bank Level | Calling down
--
{ @LF5 [False] }
--
Bottom Bank Level
R38>Bank Level | Calling up
--
{ @LFL [False] }
--
Middle Bank Level
R38>Bank Level | Calling down | Calling up
--
{ @LF4  [False] [False] }
{ @LF3  [False] [False] }
{ @LF2  [True] [False] }
{ @LF1  [False] [False] }
--
Building
Name | Average floor gap
--
{ [Pigsley Central] [3.2] }
--
Shaft Level
Shaft | Floor
--
{ [S1] [5] }
{ [S1] [4] }
{ [S1] [3] }
{ [S1] [2] }
{ [S1] [1] }
{ [S1] [L] }
{ [S2] [5] }
{ [S2] [4] }
{ [S2] [3] }
{ [S2] [2] }
{ [S2] [1] }
{ [S2] [L] }
--
Accessible Shaft Level
Shaft | Floor | Bank | Stop requested
--
{ [S2] [5]  [Lower Floors] [False] } > NOT REQUESTED
{ [S2] [4]  [Lower Floors] [False] } > NOT REQUESTED
{ [S2] [3]  [Lower Floors] [False] } > NOT REQUESTED
{ [S2] [2]  [Lower Floors] [False] } > NOT REQUESTED
{ [S2] [1]  [Lower Floors] [False] } > NOT REQUESTED
{ [S2] [L]  [Lower Floors] [False] } > NOT REQUESTED
{ [S1] [5]  [Lower Floors] [False] } > NOT REQUESTED
{ [S1] [4]  [Lower Floors] [False] } > NOT REQUESTED
{ [S1] [3]  [Lower Floors] [False] } > NOT REQUESTED
{ [S1] [2]  [Lower Floors] [False] } > NOT REQUESTED
{ [S1] [1]  [Lower Floors] [False] } > NOT REQUESTED
{ [S1] [L]  [Lower Floors] [False] } > NOT REQUESTED
--
