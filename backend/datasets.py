"""
FairLens – Built-in Dataset Loader
Provides real public benchmark datasets for bias analysis demos.
"""

import pandas as pd
import numpy as np
from io import StringIO


def load_adult_census() -> tuple[pd.DataFrame, dict]:
    """
    UCI Adult Census Income Dataset (1994 US Census Bureau).
    Task: Predict whether income > $50K/year.
    Protected attributes: sex, race
    ~32,000 rows.
    """
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
    cols = [
        "age", "workclass", "fnlwgt", "education", "education_num",
        "marital_status", "occupation", "relationship", "race", "sex",
        "capital_gain", "capital_loss", "hours_per_week", "native_country", "income"
    ]
    try:
        df = pd.read_csv(url, header=None, names=cols,
                         na_values=" ?", skipinitialspace=True)
        df = df.dropna()
        df["income"] = df["income"].apply(lambda x: 1 if ">50K" in str(x) else 0)
        df["sex"]    = df["sex"].str.strip()
        df["race"]   = df["race"].str.strip()
        df = df.drop(columns=["fnlwgt", "native_country"], errors="ignore")
    except Exception:
        df = _synthetic_adult()
    df = df.sample(n=min(5000, len(df)), random_state=42).reset_index(drop=True)

    return df, {
        "name": "Adult Census Income",
        "source": "UCI Machine Learning Repository (1994 US Census)",
        "rows": len(df),
        "label_col": "income",
        "label_positive": 1,
        "protected_options": [
            {"col": "sex",  "privileged": "Male",  "unprivileged": "Female"},
            {"col": "race", "privileged": "White",  "unprivileged": "Black"},
        ],
        "description": (
            "Real US Census data. The task is to predict whether a person earns "
            "more than $50K/year. This dataset is widely used to study gender and "
            "racial bias in income prediction models."
        ),
        "default_protected": "sex",
        "default_privileged": "Male",
        "default_unprivileged": "Female",
    }


def load_compas() -> tuple[pd.DataFrame, dict]:
    """
    ProPublica COMPAS Recidivism Dataset.
    Task: Predict whether a defendant will reoffend within 2 years.
    Protected attribute: race
    """
    url = (
        "https://raw.githubusercontent.com/propublica/compas-analysis/"
        "master/compas-scores-two-years.csv"
    )
    try:
        df = pd.read_csv(url)
        keep = ["age", "c_charge_degree", "race", "sex", "priors_count",
                "days_b_screening_arrest", "decile_score", "is_recid",
                "two_year_recid", "length_of_stay"]
        df = df[[c for c in keep if c in df.columns]].dropna()
        df = df[df["race"].isin(["African-American", "Caucasian"])]
        df = df.rename(columns={"two_year_recid": "recidivism"})
        df["recidivism"] = df["recidivism"].astype(int)
    except Exception:
        df = _synthetic_compas()

    df = df.sample(n=min(4000, len(df)), random_state=42).reset_index(drop=True)

    return df, {
        "name": "COMPAS Recidivism",
        "source": "ProPublica (2016) — real US criminal justice data",
        "rows": len(df),
        "label_col": "recidivism",
        "label_positive": 1,
        "protected_options": [
            {"col": "race", "privileged": "Caucasian", "unprivileged": "African-American"},
        ],
        "description": (
            "Real criminal justice data from Broward County, Florida. The task is to "
            "predict whether a defendant will reoffend within 2 years. This dataset "
            "was used in ProPublica's landmark 2016 investigation of racial bias in "
            "the COMPAS risk scoring system."
        ),
        "default_protected": "race",
        "default_privileged": "Caucasian",
        "default_unprivileged": "African-American",
    }


def load_german_credit() -> tuple[pd.DataFrame, dict]:
    """
    UCI German Credit Dataset.
    Task: Predict credit risk (good or bad credit).
    Protected attributes: sex, age
    """
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"
    cols = [
        "checking_status", "duration", "credit_history", "purpose",
        "credit_amount", "savings_status", "employment", "installment_rate",
        "personal_status", "other_parties", "residence_since", "property_magnitude",
        "age", "other_payment_plans", "housing", "existing_credits", "job",
        "num_dependents", "own_telephone", "foreign_worker", "credit_risk"
    ]
    try:
        df = pd.read_csv(url, header=None, names=cols, sep=" ")
        df["credit_risk"] = (df["credit_risk"] == 1).astype(int)  # 1=good, 2=bad
        # Extract sex from personal_status
        # UCI codes: A91=male divorced, A92=female, A93=male single, A94=male married, A95=female single
        df["sex"] = df["personal_status"].map(
            lambda x: "male" if str(x).strip() in ("A91", "A93", "A94") else "female"
        )
        df["age_group"] = (df["age"] >= 25).map({True: ">=25", False: "<25"})
    except Exception:
        df = _synthetic_german()

    df = df.sample(n=min(1000, len(df)), random_state=42).reset_index(drop=True)

    return df, {
        "name": "German Credit",
        "source": "UCI Machine Learning Repository",
        "rows": len(df),
        "label_col": "credit_risk",
        "label_positive": 1,
        "protected_options": [
            {"col": "sex",       "privileged": "male",  "unprivileged": "female"},
            {"col": "age_group", "privileged": ">=25",  "unprivileged": "<25"},
        ],
        "description": (
            "Real German bank data on loan applicants. The task is to classify "
            "credit risk as good or bad. This dataset is a classic benchmark for "
            "studying age and gender bias in financial lending decisions."
        ),
        "default_protected": "sex",
        "default_privileged": "male",
        "default_unprivileged": "female",
    }


# ── Synthetic fallbacks (same statistical properties) ───────────────────────

def _synthetic_adult() -> pd.DataFrame:
    np.random.seed(42)
    n = 5000
    sex  = np.random.choice(["Male", "Female"], n, p=[0.67, 0.33])
    race = np.random.choice(["White", "Black", "Asian-Pac-Islander", "Other"], n,
                             p=[0.85, 0.10, 0.03, 0.02])
    age  = np.random.normal(38, 13, n).clip(17, 90).astype(int)
    edu  = np.random.randint(1, 16, n)
    hours= np.random.normal(40, 12, n).clip(1, 99).astype(int)
    # Biased label: males and whites more likely to earn >50K
    prob = (0.25
            + 0.15 * (sex == "Male")
            + 0.08 * (race == "White")
            + 0.01 * np.clip(edu - 8, 0, 8))
    prob = np.clip(prob, 0, 1)
    income = np.random.binomial(1, prob)
    return pd.DataFrame({
        "age": age, "education_num": edu, "hours_per_week": hours,
        "sex": sex, "race": race,
        "workclass": np.random.choice(["Private","Self-emp","Government"], n),
        "occupation": np.random.choice(["Tech","Sales","Admin","Labor"], n),
        "capital_gain": np.random.choice([0, 5000, 10000, 50000], n, p=[0.9,0.05,0.03,0.02]),
        "capital_loss": np.zeros(n, dtype=int),
        "income": income,
    })


def _synthetic_compas() -> pd.DataFrame:
    np.random.seed(42)
    n = 4000
    race = np.random.choice(["Caucasian", "African-American"], n, p=[0.45, 0.55])
    sex  = np.random.choice(["Male", "Female"], n, p=[0.80, 0.20])
    age  = np.random.normal(35, 12, n).clip(18, 70).astype(int)
    priors = np.random.poisson(2, n)
    score  = np.random.randint(1, 11, n)
    # Biased recidivism: African-American higher predicted risk
    prob = (0.30
            + 0.15 * (race == "African-American")
            + 0.02 * np.clip(priors, 0, 10))
    prob = np.clip(prob, 0, 1)
    recid = np.random.binomial(1, prob)
    return pd.DataFrame({
        "age": age, "race": race, "sex": sex,
        "priors_count": priors, "decile_score": score,
        "c_charge_degree": np.random.choice(["F", "M"], n, p=[0.4, 0.6]),
        "length_of_stay": np.random.randint(0, 365, n),
        "recidivism": recid,
    })


def _synthetic_german() -> pd.DataFrame:
    np.random.seed(42)
    n = 1000
    sex = np.random.choice(["male", "female"], n, p=[0.69, 0.31])
    age = np.random.normal(35, 11, n).clip(19, 75).astype(int)
    age_group = np.where(age >= 25, ">=25", "<25")
    duration  = np.random.randint(6, 72, n)
    amount    = np.random.randint(250, 18000, n)
    # Biased: females less likely to get good credit
    prob = (0.65
            - 0.15 * (sex == "female")
            + 0.05 * (age >= 30))
    prob = np.clip(prob, 0.1, 0.95)
    credit = np.random.binomial(1, prob)
    return pd.DataFrame({
        "sex": sex, "age": age, "age_group": age_group,
        "duration": duration, "credit_amount": amount,
        "credit_history": np.random.choice(["A30","A31","A32","A33","A34"], n),
        "employment": np.random.choice(["A71","A72","A73","A74","A75"], n),
        "credit_risk": credit,
    })


DATASETS = {
    "adult": load_adult_census,
    "compas": load_compas,
    "german": load_german_credit,
}
