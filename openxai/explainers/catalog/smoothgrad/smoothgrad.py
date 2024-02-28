import torch
from ...api import BaseExplainer
from captum.attr import NoiseTunnel
from captum.attr import Saliency


class SmoothGrad(BaseExplainer):
    """
    Provides SmoothGrad attributions.
    Original paper: https://arxiv.org/abs/1706.03825
    Captum documentation: https://captum.ai/api/noise_tunnel.html
    """

    def __init__(self, model, n_samples: int = 500, standard_deviation: float = 0.5) -> None:
        """
        Args:
            model (torch.nn.Module): model on which to make predictions
        """

        self.n_samples = n_samples
        self.standard_deviation = standard_deviation

        super(SmoothGrad, self).__init__(model)

    def get_explanation(self, x: torch.Tensor, label: torch.Tensor, attr_method=Saliency) -> torch.tensor:
        """
        Explain an instance prediction.
        Args:
            x (torch.Tensor, [N x 1 x d] for tabular instance; [N x m x n x d] for image instance): feature tensor
            label (torch.Tensor, [N x ...]): labels to explain
        Returns:
            exp (torch.Tensor, [N x 1 x d] for tabular instance; [N x m x n x d] for image instance: instance level explanation):
        """
        self.model.eval()
        self.model.zero_grad()

        noise_tunnel = NoiseTunnel(attr_method(self.model))

        attribution = noise_tunnel.attribute(x,
                                             nt_type='smoothgrad',
                                             target=label,
                                             nt_samples=self.n_samples,
                                             stdevs=self.standard_deviation)

        return attribution
