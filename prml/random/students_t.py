import numpy as np
from scipy.special import gamma, digamma
from prml.random.random import RandomVariable


class StudentsT(RandomVariable):
    """
    Student's t-distribution
    p(x|mu, L(precision), dof)
    = (1 + (x-mu)^T @ L @ (x - mu) / dof)^-(D + dof)/2 / const.
    """

    def __init__(self, mu=None, precision=None, dof=None):
        assert dof is None or isinstance(dof, (int, float))
        self.mu = mu
        self.precision = precision
        self.dof = dof

    def __setattr__(self, name, value):
        if name is "mu":
            if isinstance(value, (int, float)):
                self.ndim = 1
                object.__setattr__(self, name, np.array([value]))
            elif isinstance(value, np.ndarray):
                assert value.ndim == 1
                self.ndim = value.size
                object.__setattr__(self, name, value)
            else:
                assert value is None, (
                    "mu must be either int, float, np.ndarray, or None"
                )
                object.__setattr__(self, name, None)
        elif name is "precision":
            if isinstance(value, (int, float)):
                object.__setattr__(self, name, np.eye(self.ndim) * value)
            elif isinstance(value, np.ndarray):
                assert value.shape == (self.ndim, self.ndim)
                np.linalg.cholesky(value)
                object.__setattr__(self, name, value)
            else:
                assert value is None, (
                    "precision must be either int, float, np.ndarray, or None"
                )
                object.__setattr__(self, name, None)
        else:
            object.__setattr__(self, name, value)


    def __repr__(self):
        return (
            "Student's T"
            "(\nmu={0.mu},\nprecision=\n{0.precision},\ndof={0.dof}\n)"
            .format(self)
        )

    @property
    def mean(self):
        if self.dof > 1:
            return self.mu
        else:
            raise AttributeError

    @property
    def var(self):
        if self.dof > 2:
            return np.linalg.inv(self.precision) * self.dof / (self.dof - 2)
        else:
            raise AttributeError

    def _ml(self, X):
        self.mu = np.mean(X, axis=0)
        self.precision = np.linalg.inv(np.atleast_2d(np.cov(X.T)))
        self.dof = 1
        params = np.hstack(
            (self.mu.ravel(),
             self.precision.ravel(),
             self.dof)
        )
        while True:
            E_eta, E_lneta = self._expectation(X)
            self._maximization(X, E_eta, E_lneta)
            new_params = np.hstack(
                (self.mu.ravel(),
                 self.precision.ravel(),
                 self.dof)
            )
            if np.allclose(params, new_params):
                break
            else:
                params = new_params

    def _expectation(self, X):
        d = X - self.mu
        a = 0.5 * (self.dof + self.ndim)
        b = 0.5 * (self.dof + np.sum(d @ self.precision * d, -1))
        E_eta = a / b
        E_lneta = digamma(a) - np.log(b)
        return E_eta, E_lneta

    def _maximization(self, X, E_eta, E_lneta):
        self.mu = np.sum(E_eta[:, None] * X) / np.sum(E_eta)
        d = X - self.mu
        self.precision = np.linalg.inv(
            np.atleast_2d(np.cov(E_eta ** 0.5 * d.T, bias=True))
        )
        N = len(X)
        self.dof += 0.01 * (
            N * np.log(0.5 * self.dof) + N
            - N * digamma(0.5 * self.dof)
            + np.sum(E_lneta - E_eta)
        )

    def _pdf(self, X):
        d = X - self.mu
        D_sq = np.sum(d @ self.precision * d, -1)
        return (
            gamma(0.5 * (self.dof + 1))
            * np.linalg.det(self.precision) ** 0.5
            * (1 + D_sq / self.dof) ** (-0.5 * (self.ndim + self.dof))
            / gamma(self.dof * 0.5)
            / np.power(np.pi * self.dof, 0.5 * self.ndim))
