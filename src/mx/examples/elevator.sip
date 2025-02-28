scenario : Simple Elevator
--
Shaft
ID | In service | R1>Bank
--
{ [S1] [true] @L }
{ [S2] [true] @L }
{ [S3] [true] @L }
{ [S4] [true] @P }
{ [S5] [true] @P }
{ [S6] [true] @F }
--
Door
Shaft | Close attempts | Lock requested | Held | Blocked | Emergency hold
--
{ [S1] [0] [false] [false] [false] [false] }
{ [S2] [0] [false] [false] [false] [false] }
{ [S3] [0] [false] [false] [false] [false] }
{ [S4] [0] [false] [false] [false] [false] }
{ [S5] [0] [false] [false] [false] [false] }
{ [S6] [0] [false] [false] [false] [false] }
--
Bank
Name | Passenger load time | Block clear time | Max close attempts | Average cabin speed | Average stop duration
--
L { [Lower]     [4.0] [2.0] [25] [7.0] [9.0] }
P { [Penthouse] [4.0] [2.0] [25] [7.0] [9.0] }
F { [Freight]   [7.0] [5.0] [25] [5.0] [14.0] }
--
Cabin
Shaft | Travel direction | Current floor
--
{ [S1] [.up]   [L] }
{ [S2] [.down] [2] }
{ [S3] [.up]   [G1] }
{ [S4] [.down] [P] }
{ [S5] [.up]   [L] }
{ [S6] [.down] [7] }
--
Floor
Name | Height
--
{ [PH] [35.2] }
{ [8]  [32.0] }
{ [7]  [28.8] }
{ [6]  [25.6] }
{ [5]  [22.4] }
{ [4]  [19.2] }
{ [3]  [16.0] }
{ [2]  [12.8] }
{ [1]  [9.6] }
{ [L]  [6.4] }
{ [P1] [3.2] }
{ [P2] [0.0] }
--
Bank Level
Bank | Floor
--
PPH  { [Penthouse]    [PH] }
P8   { [Penthouse]    [8] }
PL   { [Penthouse]    [L] }
PP1  { [Penthouse]    [P1] }
LF7  { [Lower Floors] [7] }
LF6  { [Lower Floors] [6] }
LF5  { [Lower Floors] [5] }
LF4  { [Lower Floors] [4] }
LF3  { [Lower Floors] [3] }
LF2  { [Lower Floors] [2] }
LF1  { [Lower Floors] [1] }
LFL  { [Lower Floors] [L] }
LFP1 { [Lower Floors] [P1] }
LFP2 { [Lower Floors] [P2] }
FPH  { [Freight]      [PH] }
F8   { [Freight]      [8] }
F7   { [Freight]      [7] }
F6   { [Freight]      [6] }
F5   { [Freight]      [5] }
F4   { [Freight]      [4] }
F3   { [Freight]      [3] }
F2   { [Freight]      [2] }
F1   { [Freight]      [1] }
FL   { [Freight]      [L] }
FP1  { [Freight]      [P1] }
FP2  { [Freight]      [P2] }
--
Top Bank Level
R38>Bank Level, R5>Bank | Calling down
--
{ @PPH @P [false] }
{ @LF7 @L [false] }
{ @FPH @F [false] }
--
Bottom Bank Level
R38>Bank Level, R6>Bank | Calling up
--
{ @PP1  @P [false] }
{ @LFP2 @L [false] }
{ @FP2  @F [false] }
--
Middle Bank Level
R38>Bank Level | Calling down | Calling up
--
{ @P8   [false] [false] }
{ @PL   [false] [false] }
{ @PP1  [false] [false] }
{ @LF6  [false] [false] }
{ @LF5  [false] [false] }
{ @LF4  [false] [false] }
{ @LF3  [false] [false] }
{ @LF2  [false] [false] }
{ @LF1  [false] [false] }
{ @LFL  [false] [false] }
{ @LFP1 [false] [false] }
{ @F8   [false] [false] }
{ @F7   [false] [false] }
{ @F6   [false] [false] }
{ @F5   [false] [false] }
{ @F4   [false] [false] }
{ @F3   [false] [false] }
{ @F2   [false] [false] }
{ @F1   [false] [false] }
{ @FL   [false] [false] }
{ @FP1  [false] [false] }
--
Building
Name | Average floor gap
--
{ [Pigsley Central] [3.2] }
--
Shaft Level
Shaft | Floor
--
{ [S1] [PH] }
{ [S1] [8] }
{ [S1] [7] }
{ [S1] [6] }
{ [S1] [5] }
{ [S1] [4] }
{ [S1] [3] }
{ [S1] [2] }
{ [S1] [1] }
{ [S1] [L] }
{ [S1] [P1] }
{ [S1] [P2] }
{ [S2] [PH] }
{ [S2] [8] }
{ [S2] [7] }
{ [S2] [6] }
{ [S2] [5] }
{ [S2] [4] }
{ [S2] [3] }
{ [S2] [2] }
{ [S2] [S1] }
{ [S2] [L] }
{ [S2] [PS1] }
{ [S2] [P2] }
{ [S3] [PH] }
{ [S3] [8] }
{ [S3] [7] }
{ [S3] [6] }
{ [S3] [5] }
{ [S3] [4] }
{ [S3] [3] }
{ [S3] [2] }
{ [S3] [1] }
{ [S3] [L] }
{ [S3] [P1] }
{ [S3] [P2] }
{ [S4] [PH] }
{ [S4] [8] }
{ [S4] [7] }
{ [S4] [6] }
{ [S4] [5] }
{ [S4] [4] }
{ [S4] [S3] }
{ [S4] [2] }
{ [S4] [1] }
{ [S4] [L] }
{ [S4] [P1] }
{ [S4] [P2] }
{ [S5] [PH] }
{ [S5] [8] }
{ [S5] [7] }
{ [S5] [6] }
{ [S5] [5] }
{ [S5] [4] }
{ [S5] [3] }
{ [S5] [2] }
{ [S5] [1] }
{ [S5] [L] }
{ [S5] [P1] }
{ [S5] [P2] }
{ [S6] [PH] }
{ [S6] [8] }
{ [S6] [7] }
{ [S6] [6] }
{ [S6] [S5] }
{ [S6] [4] }
{ [S6] [3] }
{ [S6] [2] }
{ [S6] [1] }
{ [S6] [L] }
{ [S6] [P1] }
{ [S6] [P2] }
--
Accessible Shaft Level
Shaft | Floor | Bank | Stop requested
--
{ [S6] [PH] [Freight]      [false] }
{ [S6] [8]  [Freight]      [false] }
{ [S6] [7]  [Freight]      [false] }
{ [S6] [6]  [Freight]      [false] }
{ [S6] [5]  [Freight]      [false] }
{ [S6] [4]  [Freight]      [false] }
{ [S6] [3]  [Freight]      [false] }
{ [S6] [2]  [Freight]      [false] }
{ [S6] [1]  [Freight]      [false] }
{ [S6] [L]  [Freight]      [false] }
{ [S6] [P1] [Freight]      [false] }
{ [S6] [P2] [Freight]      [false] }
{ [S1] [PH] [Penthouse]    [false] }
{ [S1] [8]  [Penthouse]    [false] }
{ [S1] [L]  [Penthouse]    [false] }
{ [S1] [P1] [Penthouse]    [false] }
{ [S2] [PH] [Penthouse]    [false] }
{ [S2] [8]  [Penthouse]    [false] }
{ [S2] [L]  [Penthouse]    [false] }
{ [S2] [P1] [Penthouse]    [false] }
{ [S3] [7]  [Lower Floors] [false] }
{ [S3] [6]  [Lower Floors] [false] }
{ [S3] [5]  [Lower Floors] [false] }
{ [S3] [4]  [Lower Floors] [false] }
{ [S3] [3]  [Lower Floors] [false] }
{ [S3] [2]  [Lower Floors] [false] }
{ [S3] [1]  [Lower Floors] [false] }
{ [S3] [L]  [Lower Floors] [false] }
{ [S3] [P1] [Lower Floors] [false] }
{ [S3] [P2] [Lower Floors] [false] }
{ [S4] [7]  [Lower Floors] [false] }
{ [S4] [6]  [Lower Floors] [false] }
{ [S4] [5]  [Lower Floors] [false] }
{ [S4] [4]  [Lower Floors] [false] }
{ [S4] [3]  [Lower Floors] [false] }
{ [S4] [2]  [Lower Floors] [false] }
{ [S4] [1]  [Lower Floors] [false] }
{ [S4] [L]  [Lower Floors] [false] }
{ [S4] [P1] [Lower Floors] [false] }
{ [S4] [P2] [Lower Floors] [false] }
{ [S5] [7]  [Lower Floors] [false] }
{ [S5] [6]  [Lower Floors] [false] }
{ [S5] [5]  [Lower Floors] [false] }
{ [S5] [4]  [Lower Floors] [false] }
{ [S5] [3]  [Lower Floors] [false] }
{ [S5] [2]  [Lower Floors] [false] }
{ [S5] [1]  [Lower Floors] [false] }
{ [S5] [L]  [Lower Floors] [false] }
{ [S5] [P1] [Lower Floors] [false] }
{ [S5] [P2] [Lower Floors] [false] }
--
