from math import log10, log2, log
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from copy import deepcopy


def process_data(dataset):
    dataset['alpha'] = dataset['alpha'].apply(lambda x: log10(x))
    dataset.drop(['id'], axis=1, inplace=True)
    # one-hot
    # dataset = pd.concat([dataset, pd.get_dummies(dataset['penalty'])], axis=1)
    # dataset.drop(['penalty'], axis=1, inplace=True)

    # categorial
    df = pd.Categorical(dataset.penalty)
    dataset['penalty'] = df.codes

    max_jobs = dataset['n_jobs'].max()
    dataset['n_jobs'] = dataset['n_jobs'].apply(lambda x: max_jobs if x == -1 else x)
    return dataset


def to_log_label(origin_label):
    return pd.Series(origin_label).apply(lambda x: log10(x))


def resume_from_log_label(encoded_label):
    return pd.Series(encoded_label).apply(lambda x: 10.0 ** x)


class Normalizer:
    scaler = MinMaxScaler()

    def __init__(self, train_data):
        self.scaler.fit(train_data)

    def get_normalized_data(self, dataset):
        return self.scaler.transform(dataset)


import pandas as pd
import numpy as np
np.set_printoptions(suppress=True)

from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error
from sklearn import preprocessing
from sklearn.model_selection import cross_val_score, KFold

from xgboost import XGBRegressor, DMatrix, cv
import matplotlib.pyplot as plt


def get_scatter(data_features, label):
    keys = data_features.columns
    for k in keys:
        plt.scatter(data_features[k], label)
        plt.xlabel(k)
        plt.ylabel("time")
        plt.show()


if __name__ == "__main__":
    data = pd.read_csv("./data/train.csv")
    test_data = pd.read_csv("./data/test.csv")

    train_data = data.iloc[:, :-1]
    train_label = data.iloc[:, -1]

    train_num = train_data.shape[0]
    all_data = pd.concat([train_data, test_data])
    all_data = process_data(all_data)

    train_data = all_data.iloc[:train_num, :]
    test_data = all_data.iloc[train_num:, :]

    train_data.to_csv("train_processed.csv")
    test_data.to_csv("test_processed.csv")

    # normalization
    feature_normalizer = Normalizer(train_data)
    train_data = pd.DataFrame(feature_normalizer.get_normalized_data(train_data), columns=all_data.columns)
    test_data = pd.DataFrame(feature_normalizer.get_normalized_data(test_data), columns=all_data.columns)

    train_data.to_csv("train_processed_normal.csv")
    test_data.to_csv("test_processed_normal.csv")

    train_label.hist()


    # regressor
    all_train_set = pd.concat([train_data, train_label], axis=1, sort=False)
    # print(all_train_set.describe())
    # corr between different attributes
    corr_matrix = all_train_set.corr()
    ax = plt.matshow(corr_matrix)
    plt.colorbar(ax)
    plt.show()
    # print(all_train_set.columns)

    # print(train_set.shape, train_label.shape, test_set.shape, test_label.shape)
    # print(train_set, train_label)

    X = all_train_set.iloc[:, :-1]
    Y = all_train_set.iloc[:, -1]

    Y = Y.apply(lambda x: to_log_label(x))
    # get_scatter(X, Y)

    Y = np.array(np.ravel(Y))
    # print(X.shape, Y.shape, Y)

    regressor = SVR(gamma='scale', C=1, epsilon=0.001, tol=1e-3)

    # regressor = SVR(degree=8, C=1, epsilon=0.2)
    regressor.fit(X, Y)
    scores = cross_val_score(regressor, X, Y, cv=20, scoring='neg_mean_squared_error')

    train_predict_label = pd.DataFrame(regressor.predict(X))
    print("train MSE:", mean_squared_error(regressor.predict(X), Y))
    print("cv MSE:", scores, np.mean(scores))

    train_predict_label_real = train_predict_label.apply(lambda x: resume_from_log_label(x))
    print("real train MSE", mean_squared_error(train_predict_label_real, Y))
    pd.concat([all_train_set, train_predict_label_real], axis=1).to_csv("train_predict_result.csv")
    # compute real cv error
    kf = KFold(n_splits=10, shuffle=True)
    cv_err = []
    regressor_cv = deepcopy(regressor)
    X = np.array(X)
    for train_idx, test_idx in kf.split(X, y=Y):
        # print("train:", train_idx, "test:", test_idx)
        train_X, test_X, train_Y, test_Y = X[train_idx], X[test_idx], Y[train_idx], Y[test_idx]
        regressor_cv.fit(train_X, y=train_Y)
        cv_predict = regressor_cv.predict(test_X)
        cv_predict_real = np.vectorize(resume_from_log_label)(cv_predict)
        test_Y_real = np.vectorize(resume_from_log_label)(test_Y)
        mse_cv = mean_squared_error(cv_predict_real, test_Y_real)
        cv_err.append(mse_cv)
    print("cv real err:", cv_err, "\n cv mean mse:", np.mean(np.array(cv_err)), "cv mse std:", np.std(np.array(cv_err)))

    predict_result = regressor.predict(test_data)
    # predict_result[predict_result<0] = train_label.min()
    # pd.DataFrame(predict_result, columns=['time']).to_csv("result.csv")
    # print(predict_result)

    predict_result = pd.DataFrame(predict_result, columns=['time'])
    predict_result = predict_result.apply(lambda x: resume_from_log_label(x))
    predict_result.to_csv("result_%2.2f.csv" % (np.mean(scores)))
    pd.concat([test_data, predict_result], axis=1).to_csv('result_full.csv')
    # print(np.array(predict_result))
