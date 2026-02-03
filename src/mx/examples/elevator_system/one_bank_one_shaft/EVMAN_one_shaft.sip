scenario : One Bank One Shaft
--
Bank
Name | Passenger load time | Block clear time | Max close attempts | Average cabin speed | Average stop duration
--
Main { [Main]     [4.0] [2.0] [25] [7.0] [9.0] }
--
Cabin
Shaft | Travel direction | Current floor
--
{ [S1] [up]   [L]  } > PICKUP DROPOFF
--
Door
Shaft | Close attempts | Lock requested | Held | Blocked | Emergency hold
--
{ [S1] [0] [False] [False] [False] [False] } > CLOSED
--
Shaft
ID | In service | R1>Bank
--
{ [S1] [True] @Main } R53> NO TRANSFER > IDLE
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
MF5  { [Main] [5] }
MF4  { [Main] [4] }
MF3  { [Main] [3] }
MF2  { [Main] [2] }
MF1  { [Main] [1] }
MFL  { [Main] [L] }
--
Top Bank Level
R38>Bank Level | Calling down
--
{ @MF5 [False] }
--
Bottom Bank Level
R38>Bank Level | Calling up
--
{ @MFL [False] }
--
Middle Bank Level
R38>Bank Level | Calling down | Calling up
--
{ @MF4  [False] [False] }
{ @MF3  [False] [False] }
{ @MF2  [False] [False] }
{ @MF1  [False] [False] }
--
Building
Name | Average floor gap
--
{ [Nakatomi Plaza] [3.2] }
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
--
Accessible Shaft Level
Shaft | Floor | Bank | Stop requested
--
{ [S1] [5]  [Main] [False] } > NOT REQUESTED
{ [S1] [4]  [Main] [False] } > NOT REQUESTED
{ [S1] [3]  [Main] [False] } > NOT REQUESTED
{ [S1] [2]  [Main] [False] } > NOT REQUESTED
{ [S1] [1]  [Main] [False] } > NOT REQUESTED
{ [S1] [L]  [Main] [False] } > NOT REQUESTED
--
