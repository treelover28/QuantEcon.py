"""
Classes for generating and plotting impulse response functions.

@author : David R. Pugh
@date : 2014-10-06

"""
import matplotlib.pyplot as plt
import numpy as np


class ImpulseResponse(object):
    """Base class representing an impulse response function for a Model."""

    # number of points to use for "padding"
    N = 10

    # length of impulse response
    T = 100

    def __init__(self, model):
        """
        Create an instance of the ImpulseResponse class.

        Parameters
        ----------
        model : model.Model
            Instance of the model.Model class representing a Solow model.

        """
        self.model = model

    @property
    def _padding(self):
        """
        Impulse response functions are "padded" for pretty plotting.

        :getter: Return the current "padding" values.
        :type: numpy.ndarray

        """
        return np.hstack((self._padding_time, self._padding_variables))

    @property
    def _padding_scaling_factor(self):
        """
        Scaling factor used in constructing the impulse response function
        "padding".

        :getter: Return the current scaling factor.
        :type: numpy.ndarray

        """
        # extract the relevant parameters
        A0 = self.model.params['A0']
        L0 = self.model.params['L0']
        g = self.model.params['g']
        n = self.model.params['n']

        if self.kind == 'per_capita':
            factor = A0 * np.exp(g * self._padding_time)
        elif self.kind == 'levels':
            factor = A0 * L0 * np.exp((g + n) * self._padding_time)
        else:
            factor = np.ones(self.N)

        return factor.reshape((self.N, 1))

    @property
    def _padding_time(self):
        """
        The independent variable, time, is "padded" using values from -N to -1.

        :getter: Return the current "padding" values.
        :type: numpy.ndarray

        """
        return np.linspace(-self.N, -1, self.N).reshape((self.N, 1))

    @property
    def _padding_variables(self):
        """
        Impulse response functions for endogenous variables are "padded" with
        N periods of steady state values.

        :getter: Return current "padding" values.
        :kind: numpy.ndarray

        """
        # economy is initial in steady state
        k0 = self.model.steady_state
        y0 = self.model.evaluate_intensive_output(k0)
        c0 = self.model.evaluate_consumption(k0)
        i0 = self.model.evaluate_actual_investment(k0)
        intitial_condition = np.array([[k0, y0, c0, i0]])

        return self._padding_scaling_factor * intitial_condition

    @property
    def _response(self):
        """
        Response functions combined independent and endogenous variables.

        :getter: Return the current response values.
        :type: numpy.ndarray

        """
        return np.hstack((self._response_time, self._response_variables))

    @property
    def _response_time(self):
        """
        The independent variable, time, for the response ranges from 0 to T.

        :getter: Return the current resonse time values.
        :type: numpy.ndarray

        """
        return np.linspace(0, self.T, self.T + 1).reshape((self.T + 1, 1))

    @property
    def _response_variables(self):
        """
        Response of endogenous variables to exogenous impulse.

        :getter: Return the current response.
        :type: numpy.ndarray

        """
        # economy is initial in steady state
        k0 = self.model.steady_state

        # apply the impulse...
        self.model.params.update(self.impulse)

        # ...and generate the response
        soln = self.model.ivp.solve(t0=0.0, y0=k0, h=1.0, T=self.T,
                                    integrator='dop853')

        # gather the results
        k = soln[:, 1][:, np.newaxis]
        y = self.model.evaluate_intensive_output(k)
        c = self.model.evaluate_consumption(k)
        i = self.model.evaluate_actual_investment(k)

        return self._response_scaling_factor * np.hstack((k, y, c, i))

    @property
    def _response_scaling_factor(self):
        """
        Scaling factor used in constructing the impulse response.

        :getter: Return the current scaling factor.
        :type: numpy.ndarray

        """
        # extract the relevant parameters
        g = self.model.params['g']
        n = self.model.params['n']
        time = np.linspace(0, self.T, self.T + 1)

        if self.kind == 'per_capita':
            factor = self._padding_scaling_factor[-1] * np.exp(g * time)
        elif self.kind == 'levels':
            factor = self._padding_scaling_factor[-1] * np.exp((g + n) * time)
        else:
            factor = np.ones(self.T + 1)

        return factor.reshape((self.T + 1, 1))

    @property
    def impulse(self):
        """
        Dictionary of new parameter values representing an impulse.

        :getter: Return the current impulse dictionary.
        :setter: Set a new impulse dictionary.
        :type: dictionary

        """
        return self._impulse

    @property
    def kind(self):
        """
        The kind of impulse response function to generate. Must be one of:
        'levels', 'per_capita', 'efficiency_units'.

        :getter: Return the current kind of impulse responses.
        :setter: Set a new value for the kind of impulse responses.
        :type: str

        """
        return self._kind

    @property
    def impulse_response(self):
        """
        Impulse response functions generated by a shock to model parameter(s).

        :getter: Return the current impulse response functions.
        :type: numpy.ndarray

        """
        orig_params = self.model.params.copy()

        # create the irf
        tmp_irf = np.vstack((self._padding, self._response))

        # reset the model parameters
        self.model.params.update(orig_params)

        return tmp_irf

    @impulse.setter
    def impulse(self, params):
        """Set a new impulse dictionary."""
        self._impulse = self._validate_impulse(params)

    @kind.setter
    def kind(self, value):
        """Set a new value for the kind attribute."""
        self._kind = self._validate_kind(value)

    def _validate_impulse(self, params):
        """Validates the impulse attribute."""
        if not isinstance(params, dict):
            mesg = "ImpulseResponse.impulse must have type dict, not {}."
            raise AttributeError(mesg.format(params.__class__))
        elif not set(params.keys()) <= set(self.model.params.keys()):
            mesg = "Invalid parameter included in the impulse dictionary."""
            raise AttributeError(mesg)
        else:
            return params

    @staticmethod
    def _validate_kind(value):
        """Validates the kind attribute."""
        valid_kinds = ['levels', 'per_capita', 'efficiency_units']

        if not (isinstance(value, str) or isinstance(value, unicode)):
            mesg = "ImpulseResponse.kind must have type str, not {}."
            raise AttributeError(mesg.format(value.__class__))
        elif value not in valid_kinds:
            mesg = "The 'kind' attribute must be in {}."
            raise AttributeError(mesg.format(valid_kinds))
        else:
            return value

    def plot_impulse_response(self, ax, variable, impulse,
                              kind='efficiency_units', log=False):
        """
        Plot an impulse response function.

        Parameters
        ----------
        ax : `matplotlib.axes.AxesSubplot`
            An instance of `matplotlib.axes.AxesSubplot`.
        variable : str
            Variable whose impulse response functions you wish to plot.
        impulse : dict
            Dictionary of new parameter values representing the impulse whose
            model response you wish to plot.
        kind : str (default='efficiency_units')
            Whether you want impulse response functions in 'levels',
            'per_capita', or 'efficiency_units'.
        log : boolean (default=False)
            Whether or not to have logarithmic scales on the vertical axes.
            Useful when plotting impulse response functions with
            kind='per_capita' or kind='levels'.

        Returns
        -------
        A list containing:

        irf_line : maplotlib.lines.Line2D
            A Line2D object representing the impulse response for the requested
            variable.
        bgp_line : maplotlib.lines.Line2D
            A Line2D object representing the pre-impulse balanced growth path
            for the model.

        """
        # generate and irf
        self.kind = kind
        self.impulse = impulse
        irf = self.impulse_response

        # create a mapping from variables to column indices
        irf_dict = {'capital': irf[:, [0, 1]],
                    'output': irf[:, [0, 2]],
                    'consumption': irf[:, [0, 3]],
                    'investment': irf[:, [0, 4]],
                    }

        # create the plot
        traj = irf_dict[variable]
        irf_line = ax.plot(traj[:, 0], traj[:, 1])

        # add the old balanced growth path
        g = self.model.params['g']
        n = self.model.params['n']
        t = self.N + traj[:, 0]

        if kind == 'per_capita':
            bgp_line = ax.plot(traj[:, 0], traj[0, 1] * np.exp(g * t), 'k--',
                               label='Original BGP')
        elif kind == 'levels':
            bgp_line = ax.plot(traj[:, 0], traj[0, 1] * np.exp((g + n) * t),
                               'k--', label='Original BGP')
        else:
            bgp_line = ax.axhline(traj[0, 1], linestyle='dashed', color='k',
                                  label='Original BGP')

        # format axes, labels, title, legend, etc
        ax.set_xlabel('Time', fontsize=15, family='serif')
        ax.set_ylabel(variable.title(), fontsize=15, family='serif')
        ax.set_ylim(0.95 * traj[:, 1].min(), 1.05 * traj[:, 1].max())

        if log is True:
            ax.set_yscale('log')

        ax.set_title('Impulse response function', fontsize=20, family='serif')
        ax.grid('on')
        ax.legend(loc=0, frameon=False, bbox_to_anchor=(1.0, 1.0),
                  prop={'family': 'serif'})

        return [irf_line, bgp_line]
