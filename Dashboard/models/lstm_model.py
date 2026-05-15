import os
import json
import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import (
    StandardScaler,
    LabelEncoder
)

from tensorflow.keras.models import (
    Model,
    load_model
)

from tensorflow.keras.layers import (
    Input,
    LSTM,
    Dense,
    Embedding,
    Flatten,
    Concatenate,
    Dropout
)

from tensorflow.keras.optimizers import Adam

# =========================================================
# CONFIG
# =========================================================

WINDOW_SIZE = 40

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_DIR = BASE_DIR

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "shared_stock_model.keras"
)

SCALER_PATH = os.path.join(
    MODEL_DIR,
    "shared_scaler.pkl"
)

ENCODER_PATH = os.path.join(
    MODEL_DIR,
    "stock_encoder.pkl"
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "metadata.json"
)

# =========================================================
# FEATURE ENGINEERING
# =========================================================

def create_features(df):

    df = df.copy()

    df["trade_date"] = pd.to_datetime(
        df["trade_date"]
    )

    df = df.sort_values(
        ["stock_code", "trade_date"]
    )

    # =========================================
    # RETURN
    # =========================================

    df["return"] = (

        df.groupby("stock_code")[
            "closing_price"
        ]

        .pct_change()

    )

    # =========================================
    # LOG RETURN
    # =========================================

    df["log_return"] = np.log(

        df["closing_price"] /

        df.groupby("stock_code")[
            "closing_price"
        ].shift(1)

    )

    # =========================================
    # VOLATILITY
    # =========================================

    df["volatility"] = (

        df.groupby("stock_code")[
            "return"
        ]

        .rolling(window=10)

        .std()

        .reset_index(0, drop=True)

    )

    # =========================================
    # REMOVE INF
    # =========================================

    df.replace(
        [np.inf, -np.inf],
        np.nan,
        inplace=True
    )

    # =========================================
    # DROP ONLY REQUIRED NA
    # =========================================

    df = df.dropna(
        subset=[
            "return",
            "log_return",
            "volatility"
        ]
    )

    df = df.reset_index(drop=True)

    return df

# =========================================================
# BUILD MODEL
# =========================================================

def build_model(
    num_stocks,
    num_features
):

    # =========================================
    # SEQUENCE INPUT
    # =========================================

    sequence_input = Input(

        shape=(
            WINDOW_SIZE,
            num_features
        ),

        name="sequence_input"

    )

    x = LSTM(
        64,
        return_sequences=True
    )(sequence_input)

    x = Dropout(0.2)(x)

    x = LSTM(64)(x)

    # =========================================
    # STOCK INPUT
    # =========================================

    stock_input = Input(
        shape=(1,),
        name="stock_input"
    )

    stock_embedding = Embedding(

        input_dim=num_stocks,

        output_dim=8

    )(stock_input)

    stock_embedding = Flatten()(
        stock_embedding
    )

    # =========================================
    # MERGE
    # =========================================

    merged = Concatenate()(
        [x, stock_embedding]
    )

    dense = Dense(
        64,
        activation="relu"
    )(merged)

    dense = Dropout(0.2)(dense)

    # =========================================
    # OUTPUTS
    # =========================================

    return_output = Dense(
        1,
        name="return_output"
    )(dense)

    log_return_output = Dense(
        1,
        name="log_return_output"
    )(dense)

    volatility_output = Dense(
        1,
        name="volatility_output"
    )(dense)

    # =========================================
    # MODEL
    # =========================================

    model = Model(

        inputs=[
            sequence_input,
            stock_input
        ],

        outputs=[

            return_output,

            log_return_output,

            volatility_output

        ]

    )

    model.compile(

        optimizer=Adam(
            learning_rate=0.0005
        ),

        loss={

            "return_output": "mse",

            "log_return_output": "mse",

            "volatility_output": "mse"

        }

    )

    return model

# =========================================================
# CREATE SEQUENCES
# =========================================================

def create_sequences(
    df,
    scaler,
    encoder
):

    feature_cols = [

        "return",

        "log_return",

        "volatility"

    ]

    scaled_features = scaler.transform(
        df[feature_cols]
    )

    X_sequence = []

    X_stock = []

    y_return = []

    y_log_return = []

    y_volatility = []

    df = df.copy()

    df["stock_id"] = encoder.transform(
        df["stock_code"]
    )

    for stock in df["stock_code"].unique():

        stock_df = df[
            df["stock_code"] == stock
        ]

        stock_scaled = scaled_features[
            stock_df.index
        ]

        stock_id = stock_df[
            "stock_id"
        ].iloc[0]

        # =====================================
        # SKIP SMALL DATA
        # =====================================

        if len(stock_df) <= WINDOW_SIZE:

            continue

        for i in range(
            WINDOW_SIZE,
            len(stock_df)
        ):

            X_sequence.append(

                stock_scaled[
                    i-WINDOW_SIZE:i
                ]

            )

            X_stock.append(stock_id)

            y_return.append(

                stock_df[
                    "return"
                ].iloc[i]

            )

            y_log_return.append(

                stock_df[
                    "log_return"
                ].iloc[i]

            )

            y_volatility.append(

                stock_df[
                    "volatility"
                ].iloc[i]

            )

    return (

        np.array(X_sequence),

        np.array(X_stock),

        {

            "return_output":
                np.array(y_return),

            "log_return_output":
                np.array(y_log_return),

            "volatility_output":
                np.array(y_volatility)

        }

    )

# =========================================================
# CHECK RETRAIN
# =========================================================

def should_retrain(df):

    if not os.path.exists(
        METADATA_PATH
    ):

        return True

    with open(
        METADATA_PATH,
        "r"
    ) as f:

        metadata = json.load(f)
    last_train_date = pd.to_datetime(
        metadata["last_train_date"]
    )

    current_date = pd.to_datetime(
        df["trade_date"].max()
    )

    return current_date > last_train_date

# =========================================================
# TRAIN MODEL
# =========================================================

def train_shared_model(
    df,
    epochs=5
):

    tf.keras.backend.clear_session()

    # =========================================
    # FEATURES
    # =========================================

    df = create_features(df)

    feature_cols = [

        "return",

        "log_return",

        "volatility"

    ]

    # =========================================
    # ENCODER
    # =========================================

    encoder = LabelEncoder()

    encoder.fit(
        df["stock_code"]
    )

    joblib.dump(
        encoder,
        ENCODER_PATH
    )

    # =========================================
    # SCALER
    # =========================================

    scaler = StandardScaler()

    scaler.fit(
        df[feature_cols]
    )

    joblib.dump(
        scaler,
        SCALER_PATH
    )

    # =========================================
    # CREATE SEQUENCES
    # =========================================

    X_sequence, X_stock, y = (

        create_sequences(
            df,
            scaler,
            encoder
        )

    )

    # =========================================
    # BUILD / LOAD MODEL
    # =========================================

    if os.path.exists(
        MODEL_PATH
    ):

        try:

            model = load_model(
                MODEL_PATH
            )

            print(
                "Loaded existing model."
            )

        except:

            model = build_model(

                num_stocks=len(
                    encoder.classes_
                ),

                num_features=len(
                    feature_cols
                )

            )

    else:

        model = build_model(

            num_stocks=len(
                encoder.classes_
            ),

            num_features=len(
                feature_cols
            )

        )

        print("Created new model.")

    # =========================================
    # TRAIN
    # =========================================

    model.fit(

        {

            "sequence_input":
                X_sequence,

            "stock_input":
                X_stock

        },

        y,

        epochs=epochs,

        batch_size=32,

        validation_split=0.1,

        verbose=1

    )

    # =========================================
    # SAVE MODEL
    # =========================================

    model.save(MODEL_PATH)

    # =========================================
    # SAVE METADATA
    # =========================================

    metadata = {

        "window_size":
            WINDOW_SIZE,

        "features":
            feature_cols,

        "stocks":
            encoder.classes_.tolist(),

        #chỉ save lại ngày tháng năm
        "last_train_date":
            str(
                df["trade_date"].max().date()
            ),

        "total_rows":
            int(len(df)),

        "total_stocks":
            int(
                df["stock_code"]
                .nunique()
            )

    }

    with open(
        METADATA_PATH,
        "w"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4
        )

    print("Model saved.")

# =========================================================
# PREDICT
# =========================================================

def predict_stock(df):

    # =========================================
    # CHECK MODEL
    # =========================================

    if not os.path.exists(
        MODEL_PATH
    ):

        raise FileNotFoundError(
            "Model not found."
        )

    # =========================================
    # FEATURE ENGINEERING
    # =========================================

    df = create_features(df)

    # =========================================
    # LOAD
    # =========================================

    model = load_model(
        MODEL_PATH
    )

    scaler = joblib.load(
        SCALER_PATH
    )

    encoder = joblib.load(
        ENCODER_PATH
    )

    feature_cols = [

        "return",

        "log_return",

        "volatility"

    ]

    stock_code = df[
        "stock_code"
    ].iloc[0]

    # =========================================
    # CHECK STOCK EXISTS
    # =========================================

    if stock_code not in encoder.classes_:

        raise ValueError(
            f"""
            Stock:
            {stock_code}

            not found in model.
            """
        )

    # =========================================
    # MIN DATA CHECK
    # =========================================

    if len(df) < WINDOW_SIZE:

        raise ValueError(
            f"""
            Need at least
            {WINDOW_SIZE}
            rows.
            """
        )

    # =========================================
    # SCALE
    # =========================================

    scaled = scaler.transform(
        df[feature_cols]
    )

    # =========================================
    # LAST WINDOW
    # =========================================

    last_sequence = scaled[
        -WINDOW_SIZE:
    ]

    X_sequence = np.expand_dims(
        last_sequence,
        axis=0
    )

    stock_id = encoder.transform(
        [stock_code]
    )

    X_stock = np.array(
        stock_id
    )

    # =========================================
    # PREDICT
    # =========================================

    predictions = model.predict(

        {

            "sequence_input":
                X_sequence,

            "stock_input":
                X_stock

        },

        verbose=0

    )

    predicted_return = (
        predictions[0][0][0]
    )

    predicted_log_return = (
        predictions[1][0][0]
    )

    predicted_volatility = (
        predictions[2][0][0]
    )

    predicted_direction = (

        "UP"

        if predicted_return > 0

        else "DOWN"

    )

    # =========================================
    # RESULT
    # =========================================

    result = {

        "stock_code":
            stock_code,

        "predicted_return":
            float(predicted_return),

        "predicted_log_return":
            float(predicted_log_return),

        "predicted_volatility":
            float(predicted_volatility),

        "predicted_direction":
            predicted_direction

    }

    return result
