# Mahalanobis vs. Euclidean distance demo

Educational demo for the *Unsung Bits* post on P. C. Mahalanobis.

## What it shows

We generate a correlated 2D Gaussian cloud (Pearson r = 0.9, both sigmas = 2).
Then we compare two test points:

| Point | Coordinates | Euclidean | Mahalanobis | Character |
|-------|-------------|-----------|-------------|-----------|
| A | (1.0, −1.0) | 1.41 | **2.24** | Against the grain - more unusual under this model |
| B | (3.0, 3.0)  | 4.24 | 1.54 | Along the main axis - plausible sample |

Euclidean distance rates A as closer to the centre. Mahalanobis rates A as more
unusual under the stated covariance model because it lies in a direction the cloud
almost never produces.

This is a toy / educational script. It is not production outlier-detection code.

## Run

```bash
pip install -r requirements.txt
python3 demo.py
```

The demo also saves `mahalanobis-ellipse-comparison.png`, containing the point cloud,
covariance ellipses, mean, and both comparison points.

## Expected output

```
========================================================
  Mahalanobis vs. Euclidean distance demo
========================================================

Covariance matrix (sigma_x = sigma_y = 2, r = 0.9):
[[4.  3.6]
 [3.6 4. ]]

Sample mean  : [+0.0539, +0.0190]
Sample cov   :
[[4.1853 3.542 ]
 [3.542  3.6791]]

Distances use the known mean and covariance that generated the cloud.

--------------------------------------------------------
Point                                    Euclidean   Mahalanobis
--------------------------------------------------------
A ( 1.0, -1.0)  [against grain]             1.4142        2.2361
B ( 3.0,  3.0)  [with grain]                4.2426        1.5390
--------------------------------------------------------

Verdict
-------
  Euclidean says 'A' is closer.
  Mahalanobis rates 'A' as more unusual.

  Point A is only 1.41 units from the centre but cuts across
  the covariance axis - a direction the cloud almost never
  produces. Mahalanobis distance: 2.24.

  Point B is 4.24 units away but lies along the main axis
  of the ellipse. Mahalanobis distance: 1.54.

  Euclidean misses the covariance pattern. Mahalanobis uses it.

  Saved geometry plot: mahalanobis-ellipse-comparison.png
========================================================
```

## Tests

```bash
python3 -m pytest test_demo.py -v
```

Eight tests covering identity, a known Euclidean value, reduction to Euclidean
distance when covariance is the identity, the central ranking reversal, a
cross-checked numerical value, and rejection of invalid covariance inputs.
