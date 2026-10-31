# Selective transaction classifier

The app ships a retrained Logistic Regression model using **note/description text only**.
It does not require subcategory, payment mode, amount, or currency. The original supplied
pickle is not executed or shipped. Inference reads numeric JSON using the existing NumPy
dependency, avoiding scikit-learn/SciPy installation on the deployed API.

## Data and reproducibility

Source: [Daily Transactions Dataset by prasad22 on Kaggle](https://www.kaggle.com/datasets/prasad22/daily-transactions-dataset).
Download and extract `Daily Household Transactions.csv`; raw financial records are not included
in the repository. Its SHA-256 is recorded in `evaluation.json`.

From the project root, in a separate training environment with backend dependencies installed:

```powershell
py -3.12 -m venv .model-venv
.model-venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r backend\ml\requirements-training.txt
.model-venv\Scripts\python.exe backend\ml\train.py --csv "PATH\Daily Household Transactions.csv"
```

Training removes duplicate rows, retains expenses and source categories with at least 15
examples, fills missing notes with empty text, and lowercases/strips text. No subcategory,
payment mode, or target-derived features enter the classifier. TF-IDF word unigrams/bigrams
and balanced Logistic Regression are fitted to training data only.

Of 2,461 raw rows, 2,127 remain across 16 source labels. Deterministic stratified splits
(`random_state=42`) use 1,275 training, 426 validation, and 426 held-out test records.
The validation set selects the maximum-coverage threshold with at least 10 accepted examples
and at least 90% observed accepted accuracy. If none qualifies, the classifier abstains on all
inputs. The test set does not select the threshold; the artifact is not refitted afterwards.

## Results for the shipped artifact

| Measure | Result |
|---|---:|
| Unfiltered 16-label test accuracy | 67.37% |
| Unfiltered macro F1 | 0.538 |
| Selected probability threshold | 0.50 |
| Validation accepted predictions | 55/426 (12.91%) |
| Validation accuracy among accepted predictions | 52/55 (94.55%) |
| Test accepted predictions | 59/426 (13.85%) |
| Test accuracy among accepted predictions | 58/59 (98.31%) |

The high selective score applies **only to accepted predictions**, not all transactions.
Coverage is measured before rules; many accepted predictions may already match app rules.
These are single-household random-split results, not an independent bank-statement benchmark.
Repeated descriptions/merchant patterns can occur across splits. Confidence scores are
uncalibrated, and there is no guarantee of these results on new users' data.

The old model's reproduced 93.19% accuracy used subcategory/payment mode/date/amount inputs.
It fell to 51.64% when subcategory and mode were unavailable. It is not the deployed classifier.

## Category mapping and fallback

| Source label | App category |
|---|---|
| Apparel | Shopping |
| Beauty | Personal Care |
| Education | Education |
| Gift | Gifts & Donations |
| Health | Healthcare |
| Money transfer | Transfer |
| Transportation | Transport |
| subscription | Subscriptions |

Food, Household, Family, Festivals, Investment, Recurring Deposit, maid, and Other abstain
because they have no sufficiently precise direct mapping to the app's taxonomy. For example,
Food combines Groceries and Dining. Blank and out-of-vocabulary text also abstain.

User overrides and existing keyword rules take priority. Only unmatched expenses reach the
model. In manual entry/editing, abstentions use the existing optional LLM fallback. Bulk imports
make no LLM calls and use `Other` when unresolved. A missing or unreadable model falls back
without failing a transaction write. Set `ML_CATEGORIZATION_ENABLED=false` to disable inference.
No schema migration or frontend changes are needed; existing records are not reclassified.

## Artifact verification

`train.py` exports vocabulary, IDF values, coefficients and intercepts to `wallet_text_model.json`
and checks inference probability parity against scikit-learn on the held-out text and smoke
inputs (maximum absolute error below 1e-10). `evaluation.json` includes the full class report,
threshold candidates, dataset hash, software version and limitations.

Future work: independently labelled bank descriptions, grouped/time-based evaluation,
broader training data, finer Food/Household labels, and calibration before expanding coverage.
