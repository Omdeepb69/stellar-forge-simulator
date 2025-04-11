import pytest
import numpy as np

# Start Dummy Model Definition (Replace with actual import: from model import Model)
class Model:
    def __init__(self, learning_rate=0.01, epochs=10):
        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0:
            raise ValueError("learning_rate must be a positive number")
        if not isinstance(epochs, int) or epochs <= 0:
            raise ValueError("epochs must be a positive integer")
        self.learning_rate = learning_rate
        self.epochs = epochs
        self._weights = None
        self.is_trained = False
        self.num_features_trained_on_ = None

    def train(self, X, y):
        if not isinstance(X, np.ndarray) or not isinstance(y, np.ndarray):
            raise TypeError("X and y must be numpy arrays")
        if X.ndim != 2:
             raise ValueError(f"X must be 2-dimensional (samples, features), got shape {X.shape}")
        if y.ndim != 1:
             raise ValueError(f"y must be 1-dimensional (samples,), got shape {y.shape}")
        if X.shape[0] != y.shape[0]:
            raise ValueError(f"X and y must have the same number of samples ({X.shape[0]} != {y.shape[0]})")
        if X.shape[0] == 0:
            raise ValueError("Training data cannot be empty")

        num_samples, num_features = X.shape
        self.num_features_trained_on_ = num_features
        self._weights = np.random.rand(num_features)
        self.is_trained = True


    def predict(self, X):
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction.")
        if not isinstance(X, np.ndarray):
            raise TypeError("X must be a numpy array")
        if X.ndim != 2:
             raise ValueError(f"X must be 2-dimensional (samples, features), got shape {X.shape}")
        if X.shape[1] != self.num_features_trained_on_:
             raise ValueError(f"Input X has {X.shape[1]} features, but model was trained on {self.num_features_trained_on_}.")

        num_samples = X.shape[0]
        predictions = X @ self._weights
        return predictions

    def evaluate(self, X, y):
        if not self.is_trained:
            raise RuntimeError("Model must be trained before evaluation.")
        if not isinstance(X, np.ndarray) or not isinstance(y, np.ndarray):
            raise TypeError("X and y must be numpy arrays")
        if X.ndim != 2:
             raise ValueError(f"X must be 2-dimensional (samples, features), got shape {X.shape}")
        if y.ndim != 1:
             raise ValueError(f"y must be 1-dimensional (samples,), got shape {y.shape}")
        if X.shape[0] != y.shape[0]:
            raise ValueError(f"X and y must have the same number of samples ({X.shape[0]} != {y.shape[0]})")
        if X.shape[1] != self.num_features_trained_on_:
             raise ValueError(f"Input X has {X.shape[1]} features, but model was trained on {self.num_features_trained_on_}.")

        predictions = self.predict(X)
        mse = np.mean((predictions - y) ** 2)
        return {"mse": mse}

    def get_params(self):
        return {"learning_rate": self.learning_rate, "epochs": self.epochs}
# End Dummy Model Definition


@pytest.fixture
def sample_data():
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
    y = np.array([1.5, 3.5, 5.5, 7.5])
    return X, y

@pytest.fixture
def untrained_model():
    return Model(learning_rate=0.1, epochs=5)

@pytest.fixture
def trained_model(untrained_model, sample_data):
    X, y = sample_data
    untrained_model.train(X, y)
    return untrained_model


def test_model_initialization_defaults():
    model = Model()
    assert model.learning_rate == 0.01
    assert model.epochs == 10
    assert not model.is_trained
    assert model._weights is None
    assert model.num_features_trained_on_ is None

def test_model_initialization_custom():
    model = Model(learning_rate=0.5, epochs=100)
    assert model.learning_rate == 0.5
    assert model.epochs == 100
    assert not model.is_trained
    assert model._weights is None

def test_model_initialization_invalid_params():
    with pytest.raises(ValueError):
        Model(learning_rate=-0.1)
    with pytest.raises(ValueError):
        Model(epochs=0)
    with pytest.raises(ValueError):
        Model(epochs=-5)
    with pytest.raises(TypeError):
        Model(learning_rate="abc")
    with pytest.raises(TypeError):
        Model(epochs=10.5)


def test_model_training(untrained_model, sample_data):
    X, y = sample_data
    model = untrained_model
    assert not model.is_trained
    assert model._weights is None

    model.train(X, y)

    assert model.is_trained
    assert model._weights is not None
    assert isinstance(model._weights, np.ndarray)
    assert model._weights.shape == (X.shape[1],)
    assert model.num_features_trained_on_ == X.shape[1]

def test_model_training_invalid_data(untrained_model, sample_data):
    X, y = sample_data
    model = untrained_model

    with pytest.raises(TypeError):
        model.train(X.tolist(), y)
    with pytest.raises(TypeError):
        model.train(X, y.tolist())

    with pytest.raises(ValueError):
        model.train(X.flatten(), y)
    with pytest.raises(ValueError):
        model.train(X, y.reshape(-1, 1))

    with pytest.raises(ValueError):
        model.train(X, y[:-1])

    with pytest.raises(ValueError):
        model.train(np.array([]).reshape(0, X.shape[1]), np.array([]))


def test_model_prediction(trained_model, sample_data):
    X, _ = sample_data
    model = trained_model
    assert model.is_trained

    predictions = model.predict(X)

    assert isinstance(predictions, np.ndarray)
    assert predictions.shape == (X.shape[0],)

def test_model_prediction_untrained(untrained_model, sample_data):
    X, _ = sample_data
    model = untrained_model
    assert not model.is_trained
    with pytest.raises(RuntimeError):
        model.predict(X)

def test_model_prediction_invalid_data(trained_model, sample_data):
    X, _ = sample_data
    model = trained_model

    with pytest.raises(TypeError):
        model.predict(X.tolist())

    with pytest.raises(ValueError):
        model.predict(X.flatten())

    X_wrong_features = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    with pytest.raises(ValueError):
        model.predict(X_wrong_features)


def test_model_evaluation(trained_model, sample_data):
    X, y = sample_data
    model = trained_model
    assert model.is_trained

    metrics = model.evaluate(X, y)

    assert isinstance(metrics, dict)
    assert "mse" in metrics
    assert isinstance(metrics["mse"], (float, np.float64))
    assert metrics["mse"] >= 0.0

def test_model_evaluation_untrained(untrained_model, sample_data):
    X, y = sample_data
    model = untrained_model
    assert not model.is_trained
    with pytest.raises(RuntimeError):
        model.evaluate(X, y)

def test_model_evaluation_invalid_data(trained_model, sample_data):
    X, y = sample_data
    model = trained_model

    with pytest.raises(TypeError):
        model.evaluate(X.tolist(), y)
    with pytest.raises(TypeError):
        model.evaluate(X, y.tolist())

    with pytest.raises(ValueError):
        model.evaluate(X.flatten(), y)
    with pytest.raises(ValueError):
        model.evaluate(X, y.reshape(-1, 1))

    with pytest.raises(ValueError):
        model.evaluate(X, y[:-1])

    X_wrong_features = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    y_wrong_features = np.array([1.0, 2.0])
    with pytest.raises(ValueError):
        model.evaluate(X_wrong_features, y_wrong_features)

def test_get_params(untrained_model):
    model = untrained_model
    params = model.get_params()
    assert isinstance(params, dict)
    assert params["learning_rate"] == 0.1
    assert params["epochs"] == 5