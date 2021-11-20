A couple of students asked me for some reference on what constitutes good vs. poor optimization on assignment 3. 

Here are some reference points, on the Stratix IV-like architecture.

All values are from the checker (geometric average transistor area over the benchmarks):

3e8 or more:  Very high area; very poor optimization

2.5e8:  High area, optimization is mediocre

2.2e8:  Good optimization

2.07e8:  Very good optimization (my reference solution hits this area). I don't expect many solutions to get to this point.  My reference solution only uses the simple mapping format, so it's definitely possible to get to this number with that format (one type of physical RAM per logical RAM). My reference solution also doesn't use the feature where two small one-port RAMs can be mapped to the same physical RAM(s).

<2.07e8:  Extremely good; you're likely in competition for best in the class.

---

- SinglePort or RAM mode logical RAM can only share physical RAM with another SinglePort or ROM RAM;

- SimpleDualPort logical RAM or TrueDualPort logical RAM cannot share physical RAM  with other RAM

- At most two logical RAM can share physical RAM with each other.

---
TODO

* [x] Functions to calculate additional LBs

* [x] Function to calculate the area?