"""External APIs."""
import numpy as np
import pandas as pd
import torch

from LoadModel import LoadModel
from Explainer import Explainer
from dataloader import return_loaders


class OpenXAI(object):
    """An OpenXAI class to serve external API calls."""

    def __init__(self, data_name: str, model_name: str, explainer_name: str):
        """Load data, model, and explainer."""
        self.data_name = data_name
        self.model_name = model_name
        self.explainer_name = explainer_name

        self.loader_train, self.loader_test = return_loaders(
            data_name=data_name, download=True)
        self.model = LoadModel(data_name=data_name, ml_model=model_name)

        dataset_tensor = torch.FloatTensor(self.loader_train.dataset.data)
        self.explainer = Explainer(method=explainer_name,
                                   model=self.model,
                                   dataset_tensor=dataset_tensor)

        # get feature names and label name
        self.feature_names = self.loader_train.dataset.feature_names
        self.label_name = self.loader_train.dataset.target_name
        self.column_names = self.feature_names
        self.column_names += [
            "attribution_{}".format(x) for x in self.feature_names
        ]
        self.column_names += ["label", "prediction", "is_test"]

        # will be calculated when the first time querying the full df
        self.df_full = None

    def _get_df_full(self):
        """Get the full dataframe."""
        # iterate through `self.loader_train` and `self.loader_test` to get and
        # store the data, predictions, and explanations on all samples
        data = []
        for X, y in self.loader_train:
            data.append(self._get_combined_data(X, y))
        for X, y in self.loader_test:
            data.append(self._get_combined_data(X, y, is_test=True))

        data = np.concatenate(data, axis=0)

        return pd.DataFrame(data, columns=self.column_names)

    def _get_combined_data(self, X, y, is_test=False):
        """Get the combined data for a single or a batch of samples.

        Let n be number of samples, d be feature dimension.

        Arguments:
          X: feature tensor with size (n, d).
          y: label tensor with size (n,).
          is_test: `True` if this batch is test data. `False` otherwise.

        Returns:
          A numpy array with n rows and 2d + 3 columns.
          The columns from left to right are: features (d),
          feature attribution scores (d), label (1), predicted label (1),
          and is_test flag (1).
        """
        attribution = self.explainer.get_explanation(X.to(dtype=torch.float32),
                                                     y)
        output = self.model(X.to(dtype=torch.float32))
        prediction = torch.argmax(output, dim=1)

        # flag indicating whether this is test data
        if is_test:
            t = torch.ones([X.size(0), 1])
        else:
            t = torch.zeros([X.size(0), 1])

        data = [X, attribution, y.unsqueeze(-1), prediction.unsqueeze(-1), t]
        data = torch.cat(data, dim=1).detach().numpy()
        return data

    def query(self, X=None, y=None):
        """Query OpenXAI to get a pandas dataframe."""
        if X is None:  # query the full data
            if self.df_full is None:
                self.df_full = self._get_df_full()
            return self.df_full
        else:  # query a batch or a single data point
            if len(X.size()) == 1:  # single data sample to batch with size 1
                X = X.unsqueeze(0)
            if len(y.size()) == 0:  # single data sample to batch with size 1
                y = y.unsqueeze(0)
            data = self._get_combined_data(X, y, is_test=True)  # assume test
            return pd.DataFrame(data, columns=self.column_names)


if __name__ == '__main__':
    # test full query
    oxai = OpenXAI(data_name="german", model_name="ann", explainer_name="lime")
    df_full = oxai.query()
    print(df_full.head())

    # test batch and single query
    model_names = ["ann", "lr"]
    data_names = ["compas", "adult", "german"]
    explainer_names = ["grad", "sg", "itg", "ig", "shap", "lime"]
    for data_name in data_names:
        _, loader_test = return_loaders(data_name=data_name, download=True)
        X, y = iter(loader_test).next()
        X = X.to(dtype=torch.float32)
        X = X[:4]  # use smaller batch
        y = y[:4]
        X_single = X[0:1]
        y_single = y[0:1]
        for model_name in model_names:
            for explainer_name in explainer_names:
                oxai = OpenXAI(data_name=data_name,
                               model_name=model_name,
                               explainer_name=explainer_name)
                df_batch = oxai.query(X, y)
                df_single1 = oxai.query(X_single, y_single)
                df_single2 = oxai.query(X_single, y_single.squeeze())
                print(data_name, model_name, explainer_name, "passed!")

    print("\n---------All tests passed!---------")
