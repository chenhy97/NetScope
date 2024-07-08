import numpy as np
import pandas as pd


def diff(frequentPatterns, R, S, th_supp, th_rr, fre_type="seq", count=None):
    '''
    @R      : test relation dataframe
    @S      : control relation dataframe
    @th_supp: threshold of support
    @th_rr  : threshold of risk ratio

    ref. @abuzaid2018diff equation(4)
    '''
    if fre_type == "item":  # diff for frequent item mining

        def sub_df(df, sub):
            return df[sub <= df['path']]

        frequentPatterns = frequentPatterns.keys()
    elif fre_type == "seq":  # diff for frequenet sequence mining

        def sub_df(df, sub):
            return df[df['path_str'].str.contains(''.join(
                ['s' + s[0] + ',' for s in sub]))]

    if count is None:

        def cal(df):
            return len(df)
    else:

        def cal(df):
            return df[count].count()

    gR, gS = len(R), len(S)
    result = []
    for pattern in frequentPatterns:
        aR = cal(sub_df(R, pattern))
        aS = len(sub_df(S, pattern))

        try:
            h_rr = (aR / (aR + aS)) / ((gR - aR) / (gR - aR + gS - aS))
        except ZeroDivisionError:
            h_rr = np.inf
        h_supp = aR / gR

        if h_rr > th_rr and h_supp > th_supp:
            result.append({
                'pattern':
                ''.join(['s' + p[0] + ',' for p in pattern]),
                'support':
                h_supp,
                'score':
                h_rr,
                'len':
                len(pattern)
            })
    return pd.DataFrame(result).sort_values(['score', 'support'],
                                            ascending=False,
                                            ignore_index=True)


def spectrum(df, switchs, method, topN=10):
    F = df[df['lier'] == 'out']
    P = df[df['lier'] == 'in']
    result = {}

    for switch in switchs:
        cf = len(F)
        cef = len(F[set([switch]) <= F['path']])
        cnf = cf - cef
        cp = len(P)
        cep = len(P[set([switch]) <= P['path']])
        cnp = cp - cep

        # print(ef, nf, ep, np)

        # Dstar2
        if method == "dstar2":
            result[switch] = cef * cef / (cep + cnf)

        # Ochiai
        elif method == "ochiai":
            result[switch] = cef / np.sqrt((cep + cef) * (cef + cnf))

        # Op2
        elif method == "op2":
            result[switch] = cef - (cep / (cep + cnp + 1))

        elif method == "ochiai2":
            result[switch] = cef * cnp / \
                np.sqrt((cef + cep) * (cnf + cnp) * (cef + cnp) * (cnf + cep))

        elif method == "sbi":
            result[switch] = 1 - cep / (cef + cep)

        elif method == "jaccard":
            result[switch] = cef / (cef + cep + cnf)

        elif method == "kulczynski":
            result[switch] = cef / (cep + cnf)

        # Tarantula
        elif method == "tarantula":
            result[switch] = cef / (cef + cnf) / \
                (cef / (cef + cnf) + cep / (cep + cnp))

    # Top-n node list
    top_list = []
    score_list = []
    print("\n %s Spectrum Result:" % method)
    for index, score in enumerate(
            sorted(result.items(), key=lambda x: x[1], reverse=True)):
        if index < topN + 6:
            top_list.append(score[0])
            score_list.append(score[1])
            print('%-50s: %.8f' % (score[0], score[1]))

    return result
