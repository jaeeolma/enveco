# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_tabular.ipynb (unless otherwise specified).

__all__ = ['get_lidar_feature', 'get_image_procs', 'EnvecoPreprocessor', 'RegressionInterpretation',
           'plot_sklearn_regression', 'adjusted_R2Score', 'rrmse', 'bias', 'bias_pct', 'ANNEnsemble', 'load_ensemble']

# Cell
from fastai.tabular.all import *
from fastai.data.all import *
from fastai.vision.data import get_grid
from .las import *
from .image import *
import matplotlib.patches as mpl_patches
from typing import Tuple
from fastai.metrics import R2Score

# Cell

def get_lidar_feature(row, path, feature_func, min_h:float=1.5, mask_plot=True):
    "Function for LiDAR opening and processing steps"
    las_data = las_to_df(f'{path}/{row.sampleplotid}.las')
    if mask_plot == True: las_data = mask_plot_from_lidar(las_data, row.x, row.y)
    features = feature_func(las_data, min_h)
    return features

# Cell

def get_image_procs(row, path, radius=31, mask_plot=True):
    "Function for tif opening and processing steps"
    image_data = open_geotiff(f'{path}/{row.sampleplotid}.tif')
    if mask_plot == True: image_data = mask_plot_from_image(image_data, radius=radius)
    metrics = calc_image_metrics(image_data)
    return metrics

# Cell

class EnvecoPreprocessor():

    def __init__(self, train_path, valid_path, test_path, **kwargs):
        self.train_df = pd.read_csv(train_path)
        self.train_df = self.train_df.rename(columns = lambda x: re.sub('[\.]+', '_', x))
        self.valid_df = pd.read_csv(valid_path)
        self.valid_df = self.valid_df.rename(columns = lambda x: re.sub('[\.]+', '_', x))
        self.test_df = pd.read_csv(test_path)
        self.test_df = self.test_df.rename(columns = lambda x: re.sub('[\.]+', '_', x))
        self.train_df['is_valid'] = 0
        self.valid_df['is_valid'] = 1
        self.train_val_df = pd.concat((self.train_df, self.valid_df))


    def preprocess_lidar(self, target_col, path, min_h:float=1.5, mask_plot:bool=True, height_features:bool=True,
                         point_features:bool=True, intensity_features:bool=True, height_quantiles:bool=True,
                         point_proportions:bool=True, canopy_densities:bool=True, normalize:bool=True,
                         log_y:bool=False) -> Tuple[TabularPandas, TabularPandas]:
        "Preprocess data and return (train_val, test) -tuple"
        trainval = self.train_val_df.copy()
        test = self.test_df.copy()
        feature_cols = []
        if height_features:
            print('Adding height based features')
            trainval[height_cols] = trainval.apply(lambda row: get_lidar_feature(row, path, calc_height_features,
                                                                                 min_h, mask_plot),
                                                   axis=1, result_type='expand')
            test[height_cols] = test.apply(lambda row: get_lidar_feature(row, path, calc_height_features,
                                                                         min_h, mask_plot),
                                           axis=1, result_type='expand')
            feature_cols.extend(height_cols)

        if point_features:
            print('Adding point distribution based features')
            trainval[point_cols] = trainval.apply(lambda row: get_lidar_feature(row, path, calc_point_features,
                                                                                min_h, mask_plot),
                                                   axis=1, result_type='expand')
            test[point_cols] = test.apply(lambda row: get_lidar_feature(row, path, calc_point_features,
                                                                                 min_h, mask_plot),
                                           axis=1, result_type='expand')
            feature_cols.extend(point_cols)

        if intensity_features:
            print('Adding intensity based features')
            trainval[intensity_cols] = trainval.apply(lambda row: get_lidar_feature(row, path, calc_intensity_features,
                                                                                    min_h, mask_plot),
                                                   axis=1, result_type='expand')
            test[intensity_cols] = test.apply(lambda row: get_lidar_feature(row, path, calc_intensity_features,
                                                                            min_h, mask_plot),
                                              axis=1, result_type='expand')
            feature_cols.extend(intensity_cols)

        if height_quantiles:
            print('Adding height quantiles')
            trainval[quantile_cols] = trainval.apply(lambda row: get_lidar_feature(row, path, calc_height_quantiles,
                                                                                  min_h, mask_plot),
                                                   axis=1, result_type='expand')
            test[quantile_cols] = test.apply(lambda row: get_lidar_feature(row, path, calc_height_quantiles,
                                                                           min_h, mask_plot),
                                             axis=1, result_type='expand')
            feature_cols.extend(quantile_cols)

        if point_proportions:
            print('Adding point proportions')
            trainval[proportion_cols] = trainval.apply(lambda row: get_lidar_feature(row, path, calc_point_proportions,
                                                                                    min_h, mask_plot),
                                                       axis=1, result_type='expand')
            test[proportion_cols] = test.apply(lambda row: get_lidar_feature(row, path, calc_point_proportions,
                                                                                 min_h, mask_plot),
                                               axis=1, result_type='expand')
            feature_cols.extend(proportion_cols)

        if canopy_densities:
            print('Adding canopy densities')
            trainval[density_cols] = trainval.apply(lambda row: get_lidar_feature(row, path, calc_canopy_densities,
                                                                                    min_h, mask_plot),
                                                       axis=1, result_type='expand')
            test[density_cols] = test.apply(lambda row: get_lidar_feature(row, path, calc_canopy_densities,
                                                                                 min_h, mask_plot),
                                               axis=1, result_type='expand')
            feature_cols.extend(density_cols)

        if log_y:
            trainval[target_col] = np.log1p(trainval[target_col])
            test[target_col] = np.log1p(test[target_col])

        means = []
        stds = []
        #for c in feature_cols:
        #    means.append(trainval[trainval.is_valid==0][c].mean())
        #    stds.append(trainval[trainval.is_valid==0][c].std())
        #norm_stats = np.array((means,stds))
        procs = None
        if normalize:
            procs = [Normalize]#.from_stats(*norm_stats)]
        trainval_tb = TabularPandas(trainval, procs=procs,
                                    cont_names=feature_cols, y_names=target_col,
                                    splits=ColSplitter(col='is_valid')(trainval))
        test_tb = TabularPandas(test, procs=procs,
                                cont_names=feature_cols, y_names=target_col)
        return trainval_tb, test_tb

    def preprocess_image(self, target_col, path, radius:int=31, mask_plot=True) -> Tuple[TabularPandas, TabularPandas]:
        "Preprocess dataframes and return (train_val, test) -tuple"
        # TODO
        pass

    def preprocess_lidar_and_image(self, target_col, path, min_h:float=1.5, radius:int=31,
                                   mask_plot:bool=True) -> Tuple[TabularPandas, TabularPandas]:
        "Preprocess dataframes and return (train_val, test) -tuple"
        # TODO
        pass

# Cell
from fastai.metrics import *

class RegressionInterpretation(Interpretation):
    "Interpretation for regression models"

    def __init__(self, dl, inputs, preds, targs, decoded, losses):
        super().__init__(dl, inputs, preds, targs, decoded, losses)

    def plot_results(self, title='Regression results', log_y:bool=False, **kwargs) -> plt.Axes:
        "Plot nice result image for regression tasks, code still need prettifying"
        axs = get_grid(self.dl.c, figsize=((6+1)*self.dl.c, (6)*self.dl.c)) # if we have multitarget
        if log_y:
            self.targs = torch.expm1(self.targs)
            self.preds = torch.expm1(self.preds)
        for i, a in enumerate(axs):
            im = a.scatter(self.targs[:,i], self.preds[:,i], c=torch.abs(self.targs[:,i]-self.preds[:,i]))
            a.set_xlabel('Real value')
            a.set_ylabel('Predicted value')
            a.set_title(self.dl.y_names[i])
            a.grid()
            x = np.linspace(0, max(self.preds[:,i].max(),self.targs[:,i].max()))
            a.plot(x, x, color='orange')
            cbar = plt.colorbar(im, ax=a)
            cbar.ax.set_ylabel('Deviations', rotation=90)
            res_mae = mae(self.targs[:,i], self.preds[:,i])
            res_mse = mse(self.targs[:,i], self.preds[:,i])
            res_rmse = rmse(self.targs[:,i], self.preds[:,i])
            res_rrmse = res_rmse / self.targs.mean() * 100
            r2 = R2Score()(self.preds[:,i], self.targs[:,i])
            adjusted_r2 = adjusted_R2Score(r2, self.inputs[1].shape[0], self.inputs[1].shape[1])
            res_bias = bias(self.targs[:,i], self.preds[:,i])
            res_pct_bias = bias_pct(self.targs[:,i], self.preds[:,i])

            handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white",
                       lw=0, alpha=0)] * 8
            labels = [f'MSE: {res_mse:.2f}', f'RMSE: {res_rmse:.2f}', f'RRMSE: {res_rrmse:.2f}%',
                      f'MAE: {res_mae:.2f}', f'R2: {r2:.2f}', f'Adj. R2: {adjusted_r2:.2f}',
                      f'BIAS: {res_bias:.2f}', f'BIAS-%: {res_pct_bias:.2f}%']
            a.legend(handles, labels, loc='best', fancybox=True, handlelength=0, handletextpad=0)
        if log_y:
            self.targs = torch.log1p(self.targs)
            self.preds = torch.log1p(self.preds)
        return axs

    @classmethod
    def from_ensemble(cls, ensemble, ds_idx=1, dl=None, act=None):
        "Construct interpretation object from an ensemble of learners"
        if dl is None: dl = ensemble.dls[ds_idx]
        return cls(dl, *ensemble.get_ensemble_preds(dl=dl, with_input=True, with_loss=True, with_decoded=True, act=act))

# Cell
def plot_sklearn_regression(model, X:TabularPandas, y:TabularPandas, log_y:bool=False, **kwargs) -> plt.Axes:
    "Similar plotting utility than RegressionInterpretation"
    preds = model.predict(X)
    if len(preds.shape) != 2: preds = preds[:,None]
    cols = y.columns
    y = y.values
    if log_y:
        preds = np.expm1(preds)
        y = np.expm1(y)
    axs = get_grid(y.shape[1], figsize=((6+1)*y.shape[1], (6)*y.shape[1])) # if we have multitarget
    for i, a in enumerate(axs):
        im = a.scatter(y[:,i], preds[:,i], c=np.abs(y[:,i]-preds[:,i]))
        a.set_xlabel('Real value')
        a.set_ylabel('Predicted value')
        a.set_title(cols[i])
        a.grid()
        x = np.linspace(0, max(preds[:,i].max(),y[:,i].max()))
        a.plot(x, x, color='orange')
        cbar = plt.colorbar(im, ax=a)
        cbar.ax.set_ylabel('Deviations', rotation=90)
        res_mae = mae(Tensor(y[:,i]), Tensor(preds[:,i]))
        res_mse = mse(Tensor(y[:,i]), Tensor(preds[:,i]))
        res_rmse = rmse(Tensor(y[:,i]), Tensor(preds[:,i]))
        res_rrmse = res_rmse / y.mean() * 100
        r2 = R2Score()(Tensor(y[:,i]), Tensor(preds[:,i]))
        adjusted_r2 = adjusted_R2Score(r2, X.shape[0], X.shape[1])
        res_bias = bias(Tensor(y[:,i]), Tensor(preds[:,i]))
        res_pct_bias = bias_pct(Tensor(y[:,i]), Tensor(preds[:,i]))
        handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white",
                   lw=0, alpha=0)] * 8
        labels = [f'MSE: {res_mse:.2f}', f'RMSE: {res_rmse:.2f}', f'RRMSE: {res_rrmse:.2f}%',
                  f'MAE: {res_mae:.2f}', f'R2: {r2:.2f}', f'Adj. R2: {adjusted_r2:.2f}',
                  f'BIAS: {res_bias:.2f}', f'BIAS-%: {res_pct_bias:.2f}%']
        a.legend(handles, labels, loc='best', fancybox=True, handlelength=0, handletextpad=0)
    return axs

# Cell
def adjusted_R2Score(r2_score, n, k):
    "Calculates adjusted_R2Score based on r2_score, number of observations (n) and number of predictor variables(k)"
    return 1 - (((n-1)/(n-k-1)) * (1 - r2_score))

def _rrmse(inp, targ):
    "RMSE normalized with mean of the target"
    return torch.sqrt(F.mse_loss(inp, targ)) / targ.mean() * 100

rrmse = AccumMetric(_rrmse)
rrmse.__doc__ = "Target mean weighted rmse"

def _bias(inp, targ):
    "Bias metric"
    inp, targ = flatten_check(inp, targ)
    return (inp - targ).sum() / len(targ)

bias = AccumMetric(_bias)
bias.__doc__ = 'Bias metric'

def _bias_pct(inp, targ):
    "Percent bias"
    inp, targ = flatten_check(inp, targ)
    return 100 * ((inp-targ).sum()/len(targ)) / targ.mean()

bias_pct = AccumMetric(_bias_pct)
bias_pct.__doc__ = 'Mean weighed bias'

# Cell
class ANNEnsemble():

    def __init__(self, dls, metrics, y_range:tuple=None, n_models=10, **learner_kwargs):
        "Create an ensemble of ANN models. TODO add option to use different parameters or different split for dataset"
        self.dls = dls
        self.metrics = metrics
        self.models = []
        for _ in range(n_models):
            # This way instead of list comprehension because possible model-specific settings
            self.models.append(tabular_learner(dls, metrics=metrics, y_range=y_range, **learner_kwargs))

    def fit_one_cycle(self, n_iterations, max_lr):
        "Fit the models"
        for m in self.models:
            m.fit_one_cycle(n_iterations, max_lr=max_lr)

    def validate(self, dl=None) -> pd.DataFrame:
        "Validate all models individually and as an ensemble"
        if dl is None: dl=self.dls[1]
        model_results = torch.cat([m.get_preds(reorder=False, dl=dl)[0] for m in self.models], dim=-1)
        ensemble_results = model_results.sum(axis=-1) / len(self.models)
        res_df = pd.DataFrame(columns=['model_identifier'] + [m.name if hasattr(m, 'name') else m.__name__ for m in self.metrics])
        res_df.loc[0] = (['ensemble']
                         + [metric(ensemble_results, Tensor(dl.y.values)).item() for metric in self.metrics])
        for i in range(len(self.models)):
            res_df.loc[i+1] = ([i]
                               + [metric(model_results[:,i], Tensor(dl.y.values)).item()  for metric in self.metrics])
        return res_df

    def get_ensemble_preds(self, ds_idx=1, dl=None, with_input=True, with_decoded=False, with_loss=False, act=None,
                           inner=False, reorder=False, cbs=None, **kwargs):
        "get_preds but ensemble results"
        if dl is None: dl=self.dls[1].new(shuffled=False, drop_last=False)
        if reorder and hasattr(dl, 'get_idxs'):
            idxs = dl.get_idxs()
            dl = dl.new(get_idxs = _ConstantFunc(idxs))
        model_results = []
        for m in self.models:
            model_results.append(m.get_preds(dl=dl, with_input=with_input, with_decoded=with_decoded, with_loss=with_loss,
                                             act=act, inner=inner, reorder=reorder, cbs=cbs, **kwargs))

        ensemble_results = []
        # iterate through results:
        obs_idx = 0
        if with_input:
            ensemble_results.append(model_results[0][obs_idx])
            obs_idx += 1
        ensemble_results.append(sum([res[obs_idx] for res in model_results])/len(self.models))
        obs_idx += 1
        ensemble_results.append(model_results[0][obs_idx])
        obs_idx += 1
        if with_decoded:
            ensemble_results.append(model_results[0][obs_idx])
            obs_idx += 1
        if with_loss:
            ensemble_results.append(sum([res[obs_idx] for res in model_results])/len(self.models))
        return tuple(ensemble_results)

    def predict(self, item):
        model_results = [m.predict(item) for m in self.models]
        ensemble_results = sum([res[-1] for res in model_results])/len(self.models)
        ensemble_dec_results = sum([res[-2] for res in model_results])/len(self.models)
        return (model_results[0][0], ensemble_dec_results, ensemble_results)


    def export(self, path, pickle_protocol=2):
        "Save each Learner in the ensemble"
        pass

def load_ensemble(path, cpu=True) -> ANNEnsemble:
    # Read config and dls
    pass