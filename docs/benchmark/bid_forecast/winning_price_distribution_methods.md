# Methods for Estimating Winning-Price and Market-Price Distributions in RTB

## Key Abbreviations

| Abbreviation | Explanation |
|---|---|
| RTB, DSP, SSP | RTB is bidding for advertising impressions in real time; a DSP is a platform for buying impressions, and an SSP is a platform for selling them. |
| CDF, PDF, PMF | CDF is the cumulative distribution function; PDF is the probability density function of a continuous variable; PMF is the probability mass function of a discrete variable. |
| KM, GBDT, LSTM | KM is the Kaplan–Meier estimator; GBDT is gradient boosting on decision trees; LSTM is a recurrent neural network with long short-term memory. |
| MLE, NLL | MLE is maximum likelihood estimation. NLL usually means negative log-likelihood; the ADM paper uses the same abbreviation for a likelihood-based neighborhood loss. |
| DLF, MDLF, TLF | DLF is deep neural-network forecasting of price distributions; MDLF is its multi-slot variant; TLF is transformer-based price-distribution forecasting. |
| MCNet, DDN | MCNet is a neural mixture-density model that accounts for censoring; DDN is a deep neural network for estimating the winning-threshold distribution in a first-price auction. |
| KMMN, ADM | KMMN is a Markov network combined with Kaplan–Meier estimation; ADM is modeling a price distribution without a prespecified parametric form. |
| ANLP, KL, MAE, RMSRE, ROC-AUC | ANLP is the mean negative log-probability of an observation under a model; KL is Kullback–Leibler divergence; MAE is mean absolute error; RMSRE is root mean squared relative error; ROC-AUC is the area under the ROC curve. |

## Problem and Terminology

This review brings together ten publications on forecasting bid and price distributions. Their central question is not merely how to estimate a mean or another single price, but how to recover the conditional price distribution for an auction request: which prices are likely, what the probability of winning is at each bid, and how uncertain the forecast is. Most works study a DSP in a second-price auction, while one studies first-price auctions and one extends the problem to multiple ad slots. These quantities must not be conflated.

Let $x$ denote request features known before bidding, $b$ the bid of the participant being considered, and $z$ the market price or required winning price. In a single-slot second-price auction, the DSP with the highest bid usually pays the second-highest bid, that is, the maximum competing bid. Under these conditions, $z$ is often called the market price, winning price, or minimum price sufficient to win. Below, “market price” refers to the random threshold price used in a particular paper, not the DSP's own bid.

The bid $b$ is the participant's decision, not an observation of the market price. In a threshold model, a win occurs when $b > z$, giving the win probability

$$
F(b\mid x)=P(z<b\mid x),\qquad S(b\mid x)=P(z\ge b\mid x)=1-F(b\mid x).
$$

$F$ is the CDF, or cumulative win probability. The **survival function** $S(b\mid x)$ gives the probability that market price $z$ is equal to or greater than bid $b$. If winning requires a bid strictly greater than the market price, then $S(b\mid x)$ is the probability of losing, or $1-F(b\mid x)$.

For a continuous price with density $f(z\mid x)$, $F(b\mid x)=\int_{-\infty}^b f(z\mid x)\,dz$. For a discrete price grid, $F$ is calculated by summing the probability masses of intervals $p_l=P(z\in V_l\mid x)$. PDF and CDF answer different questions: the density maximum identifies the mode of the price distribution, while the CDF at $b$ gives the fraction of repeated, similar auctions that bid $b$ would win.

In a first-price auction, the participant's bid is also the winner's payment. For DDN, the target is the minimum winning bid, defined by the maximum competing bid, not the second-price payment. Its distribution helps determine how far to shade the bid below the impression's value, accounting for win probability and overpayment risk. In a multi-slot auction, the ranking price for a position and the event “placing in the top k positions” also differ from a single winning price in a single-slot auction.

## Censoring: What Is Observed

With ordinary DSP logs in a second-price auction, a winning bid reveals price $z$ (through the payment, absent other rules or adjustments). A losing DSP knows only that its bid was insufficient: $z \ge b$. This is right censoring: the unknown true price lies to the right of the observed threshold. Fitting a distribution only to wins systematically overestimates mass at low prices and can consequently underestimate prices and distort the CDF.

For independent observations, the likelihood and its logarithm under right censoring are:

$$
L(\theta)=\prod_{i\in W} f_\theta(z_i\mid x_i)\;\prod_{i\in C} S_\theta(b_i\mid x_i),
\qquad
\ell(\theta)=\sum_{i\in W}\log f_\theta(z_i\mid x_i)+\sum_{i\in C}\log S_\theta(b_i\mid x_i).
$$

Notation:

- $i$ is the observation (auction) index; $x_i$ is the vector of request features known before bidding.
- $b_i$ is the bid of the participant being considered; $z_i$ is the market price in auction $i$. On a win, $z_i$ is observed; on a loss, only $z_i\ge b_i$ is known.
- $\delta_i$ is the price-observability indicator: $\delta_i=1$ for a win and $\delta_i=0$ for a loss. Accordingly, $W=\{i:\delta_i=1\}$ is the set of indices of won auctions, and $C=\{i:\delta_i=0\}$ is the set of indices of lost auctions with censored prices.
- $\theta$ is the parameter vector of the market-price distribution model.
- $f_\theta(z_i\mid x_i)$ is the conditional market-price density at $z_i$ given features $x_i$; it is the contribution from a won auction.
- $S_\theta(b_i\mid x_i)=P_\theta(z_i\ge b_i\mid x_i)$ is the conditional survival function evaluated at $b_i$. Here $P_\theta$ is probability under the model with parameters $\theta$. This contribution from a lost auction accounts for the entire distribution tail starting at $b_i$.
- $L(\theta)$ is the likelihood of the observed data under parameters $\theta$; $\ell(\theta)=\log L(\theta)$ is its natural logarithm.

This is a general principle, not a claim that all ten papers optimize exactly this formula. DLF and the transformer-based model have additional CDF loss terms, ADM uses probability mass in a neighborhood of the bid for losses, and KMMN recovers the KM estimate through observation probabilities. The choice between $b>z$ and $b\ge z$ depends on the tie-breaking rule, minimum price increment, and discretization method; the chosen condition must match the exchange rules.

Censoring is not always right censoring. In Chahuara et al., the publisher sets a floor price $f$: if $f$ exceeds the highest bid, neither top bid is observed; if $b_1\ge f>b_2$, the first bid is observed but the second is not. This is full and partial censoring of bids in the publisher-revenue estimation problem. In multi-slot MDLF, a known occupied position provides censored thresholds for other positions; the authors explicitly formulate events as placement in the top k positions to avoid conflating left and right censoring.

## Summary Table

| Work | What is estimated | Proposed approach | Censoring and training | Output and problem type |
|---|---|---|---|---|
| Cui et al. (2011) | Campaign-level bid and market-price distributions in NGD | Split a campaign into target segments, use a star-shaped tree, estimate segment lognormal-distribution parameters with GBDT, and form their weighted mixture | Forecast relies mainly on history and segment data; censored likelihood is not used | Campaign CDF; early aggregation model |
| Wang et al. (2016) | Conditional market-price distribution | Feature tree with categorical values clustered by distribution difference; KM in leaves | Jointly use observed winning prices and losing bids when estimating the survival function with KM | Nonparametric PMF and CDF in each leaf |
| Chahuara et al. (2017) | First and second bids, publisher revenue at different floor prices | Online Aalen regression for bid distributions, latent user and ad-slot factors, exponential forgetting | Left censoring of bids by the floor price; expected revenue is calculated by integrating the estimated distributions | Bid distributions and publisher revenue profile |
| Ren et al. (2019), DLF | Conditional market-price distribution and win probability | Discrete price grid; LSTM estimates conditional probability of price falling into each interval | NLL on the density of winning prices and CDF loss for wins and losses | Discrete PMFs and CDF, win probability |
| Ghosh et al. (2020), MCNet | Winning-price distribution | Heteroscedastic parametric regression followed by a neural mixture of Gaussian densities that accounts for censoring | Winning observations contribute the observed-price density; losses contribute the distribution-tail probability | Smooth mixture PDF and CDF; scalable DSP model |
| Ou et al. (2023), MDLF | Ranking price and probability of each position | Discrete price, LSTM over price with conditional loss probabilities for positions | Multiple objective terms for PDF, position, and CDF; losses and known positions provide partial labels | PMF and CDF, probabilities of occupying each rank and placing in the top k positions |
| Zhou et al. (2021), DDN | Minimum winning price in a first-price auction | Network estimates parameters $\alpha(x)$ of a selected distribution family; bid is found by golden-section search using participant expected utility | Open mode: SSP reveals the threshold to everyone regardless of outcome; MLE uses the PDF. Closed mode: only the outcome is known; Bernoulli log-loss uses the CDF | Conditional PDF and CDF of the winning threshold; optimal bid |
| KMMN (Wang et al., 2022) | Conditional market-price distribution | Markov network models price and outcome probabilities given request and bid; conditional KM estimate is then computed | Network receives wins with exact prices and losses with thresholds; KM estimate is computed from predictions | Discrete PMF and CDF for each request |
| Li et al. (2021 arXiv version), ADM | Discrete conditional price distribution | Feature extraction and normalization over price intervals with softmax; neighborhood likelihood-based loss (NLL) | Wins contribute the observed price mass and its neighborhood; losses contribute mass in the neighborhood to the right of the bid | PMF over price intervals; CDF by summation; fast forecasting |
| Yakovleva et al. (2024), TLF | Discrete conditional market-price distribution | Transformer encoder with self-attention across all price intervals; outputs define conditional price probabilities | PDF loss for wins and binary cross-entropy over the CDF for wins and losses | PMF and CDF; transfer learning for the cold-start problem |

## Contents

- [Key Abbreviations](#key-abbreviations)
- [Problem and Terminology](#problem-and-terminology)
- [Censoring: What Is Observed](#censoring-what-is-observed)
- [Summary Table](#summary-table)
- [Methods and Papers](#methods-and-papers)
  - [Cui et al. (2011)](#1-cui-et-al-2011-campaign-forecasting-as-a-mixture-of-segments)
  - [Wang et al. (2016)](#2-wang-et-al-2016-distribution-tree-and-km-in-the-leaves)
  - [Chahuara et al. (2017)](#3-chahuara-et-al-2017-bids-and-publisher-revenue-with-floor-price-censoring)
  - [Ren et al. (2019), DLF](#4-ren-et-al-2019-deep-neural-network-price-distribution-forecasting-dlf)
  - [Ghosh et al. (2020), MCNet](#5-ghosh-et-al-2020-parametric-regression-with-censoring-and-mcnet)
  - [Ou et al. (2023), MDLF](#6-ou-et-al-2023-multi-slot-mdlf)
  - [Zhou et al. (2021), DDN](#7-zhou-et-al-2021-deep-distribution-network-for-first-price-auctions-ddn)
  - [Wang et al. (2022), KMMN](#8-wang-et-al-2022-markov-network-and-kaplan-meier-estimator-kmmn)
  - [Li et al. (2021 arXiv version), ADM](#9-li-et-al-2021-arxiv-version-arbitrary-distribution-modeling-adm-and-neighborhood-likelihood)
  - [Yakovleva et al. (2024), TLF](#10-yakovleva-et-al-2024-transformer-based-price-distribution-forecasting-tlf)
- [How to Choose a Method Class](#how-to-choose-a-method-class)
- [How to Compare Results Without Methodological Errors](#how-to-compare-results-without-methodological-errors)

## Methods and Papers

### 1. Cui et al. (2011): Campaign Forecasting as a Mixture of Segments

**Source:** “Bid Landscape Forecasting in Online Ad Exchange Marketplace”

The problem is framed from the NGD exchange's perspective: an advertiser wants to know what fraction of eligible impressions will be won at a given price. The authors divide a campaign into disjoint segments, each corresponding to a combination of targeting attribute values. A star-shaped bid tree stores segment data; corresponding history templates are used for rare or new combinations. GBDT predicts the mean and standard deviation of the logarithm of the bid for a segment, and bids in the segment are described by a lognormal distribution. Segment distributions are combined into a campaign-level mixture, with weights related to expected volume and impression distribution or estimated when fitting the mixture.

In simplified form, for segments $s$:

$$
F_{campaign}(b)=\sum_s \omega_s F_s(b),\qquad
f_s(b)=\mathrm{LogNormal}(b;\mu_s,\sigma_s),\quad \omega_s\ge0,\quad\sum_s\omega_s=1.
$$

The model builds a bid distribution from segment components and relies on exchange bid history. It does not use a likelihood that accounts for censored DSP observations, where each loss only indicates the condition $z\ge b$. The authors compare two baselines: transferring the campaign's historical distribution and using a distribution concentrated at the segment's predicted mean. Across 1800 campaigns, the authors report a mean mixture RMSRE of 23,51%, versus 67,88% and 38,21% for the baselines, respectively. These results use RightMedia data.

**Practical meaning and limitations.** With enough coverage of targeting combinations, a segment mixture provides an interpretable CDF and makes each segment's contribution traceable. A lognormal form at segment level limits multimodality; large sparse trees and heuristic template selection need tuning. In general, the method does not account for right censoring in bid logs.

### 2. Wang et al. (2016): Distribution Tree and KM in the Leaves

**Source:** “Functional Bid Landscape Forecasting for Display Advertising”

The goal is to estimate the market-price distribution from features $x$ of an individual impression without imposing a common parametric form on all impressions. The authors build a tree for categorical features: attribute values are clustered so that the tree can split large categorical sets; the growth criterion uses differences between child-node distributions based on KL divergence. In each leaf, the survival function is estimated nonparametrically with Kaplan–Meier from observed winning prices and censored losing bids.

On a price grid, the KM estimate of the survival function $S(b)$ is the product of conditional event-free fractions:

$$
\hat S(b)=\prod_{j<b}\left(1-\frac{d_j}{n_j}\right),\qquad
\hat p(z=j)=\hat S(j)-\hat S(j+1),\qquad
\hat F(b)=1-\hat S(b).
$$

Here, $d_j$ is the number of observed market prices at level $j$, and $n_j$ is the number of observations still at risk at that level, including bids right-censored above the threshold. The tree partitions the sample by feature values, and the survival function is estimated separately in each leaf. A forecast for a new impression comes from its corresponding leaf.

As baselines, the authors consider a wins-only model, a survival model without a tree, a mixture model, and a survival tree. The paper reports improvement in log-likelihood and KL over the previous model on a dataset with nine advertisers.

**Practical meaning and limitations.** The approach is useful when natural categorical partitions exist and a common price curve within each leaf is reasonable. Partitioning makes a single global KM curve less coarse and allows features to be used. However, the KM tail above the highest observed price is not identifiable without assumptions or additional support, leaves can be sparse, and quality depends on the tree/discretization and data volume.

### 3. Chahuara et al. (2017): Bids and Publisher Revenue with Floor-Price Censoring

**Source:** “Real-Time Optimization of a Web Publisher RTB Revenue”

Unlike second-price forecasting problems for a DSP, here the publisher chooses a floor price $f$ in a second-price auction, where $b_1$ and $b_2$ are the first and second bids. Revenue is $\mathbf{1}_{f\le b_1} \max(f,b_2)$. Optimizing only the expected value of $b_1$ ignores the asymmetry of losses: a floor price that is too high may cause a sale to fail. The authors therefore estimate expected revenue for several discrete values of $f$ and choose the value with the highest expected revenue.

The first- and second-bid distributions are estimated separately while accounting for censoring. The method uses an additive Aalen hazard model on discrete levels with features and latent user and ad-slot factors. The estimated hazards are used to recover distributions. For left censoring, the paper uses the density-to-CDF ratio, whereas the standard right-side hazard function is $f/(1-F)$. In the factorization model, observation weights depend on age through forgetting factor $\gamma$, allowing market changes to be considered. For censored outcomes, expected revenue at each floor price is computed from the estimated distributions; this estimate is used in a separate revenue-profile regression.

Thus, the price model produces discretized CDFs and PDFs of bids, and the final decision is the floor price that maximizes estimated publisher revenue. The methods listed in §2 of the paper refer to prior work and baseline approaches used for comparison.

**Practical meaning and limitations.** The method suits a publisher that receives incomplete bid information because of an imposed floor price and must choose that floor online with low latency. It requires correct modeling of left censoring and the relationship between bids. Latent factorization and assumptions about revenue structure may not fit an arbitrary DSP. Modeling $b_1$ and $b_2$ separately does not itself describe their dependence, so expected-revenue estimates should be interpreted with that limitation in mind when bids are correlated.

### 4. Ren et al. (2019): Deep Neural Network Price-Distribution Forecasting (DLF)

**Source:** “Deep Landscape Forecasting for Real-time Bidding Advertising”

DLF discretizes price into ordered intervals $V_l$ and predicts at each step the conditional probability $h_l=P(z\in V_l \mid z\text{ is not below previous thresholds}, x)$. An LSTM processes the price intervals sequentially. The interval probabilities, survival function, and CDF are recovered from the sequence of conditional probabilities:

$$
p_l=h_l\prod_{j<l}(1-h_j),\qquad
S(b_l)=\prod_{j\le l}(1-h_j),\qquad
F(b_l)=1-S(b_l).
$$

$p_l$ is the probability mass of an interval, $F$ is the win probability at the corresponding boundary bid, and $S$ is the loss probability. The training loss combines the negative log-likelihood of observed winning prices with a Bernoulli CDF term for auction outcomes. On a win, exact price $z$ is known; on a loss, only $z\ge b$ is known.

On a finite grid, residual mass after the final interval is $S_L=\prod_{j\le L}(1-h_j)$. To obtain a normalized distribution over the entire price axis, the residual mass must be assigned to a separate tail interval or a boundary condition must be explicitly specified. This is a practical implication of the conditional-probability product formula, not a recommendation from the paper's authors.

The authors use KM, parametric distributions, and earlier censored models as baselines. The proposed model estimates conditional probabilities with an LSTM and uses the corresponding loss function. The authors show improvements on two real datasets. Metric values depend on price discretization, the historical distribution, and the evaluation protocol.

**Practical meaning and limitations.** DLF is suitable when a full conditional price distribution is needed for each request, prices can be represented on a discrete grid, and dependencies between adjacent intervals are useful to model recurrently. Narrow intervals increase model size and data sparsity; wide intervals reduce precision. The selected grid limits representation of a long or weakly observed tail. Products of $1-h_l$ make the CDF monotonic but do not guarantee calibration.

### 5. Ghosh et al. (2020): Parametric Regression with Censoring and MCNet

**Source:** “Scalable Bid Landscape Forecasting in Real-time Bidding”

The baseline is censored regression. Observed winning prices contribute their density; losses contribute the probability that price exceeds the bid. The baseline model assumes a conditional mean $\beta^\top x$ and a shared normal-error variance $\sigma^2$. The first proposed step is parametric heteroscedastic regression with censoring:

$$
W_i\sim\mathcal N(\beta^\top x_i,\sigma_i^2),\quad
\sigma_i=\exp(\alpha^\top x_i),
$$

with log-likelihood contributions $\log f(w_i\mid x_i)$ for wins and $\log P(W_i>b_i\mid x_i)$ for losses. Variance depends on features, but the conditional distribution remains normal and unimodal.

The proposed MCNet goes further: a network predicts weights $\pi_k(x)$, means $\mu_k(x)$, and scales $\sigma_k(x)$ of a Gaussian mixture:

$$
f(w\mid x)=\sum_{k=1}^{K}\pi_k(x)\frac{1}{\sigma_k(x)}\phi\!\left(\frac{w-\mu_k(x)}{\sigma_k(x)}\right),
\quad
S(b\mid x)=\sum_{k=1}^{K}\pi_k(x)\Phi\!\left(\frac{\mu_k(x)-b}{\sigma_k(x)}\right).
$$

The $\pi$ weights are normalized with softmax, and positivity of $\sigma$ is ensured by exponential parameterization. The objective sums log densities for wins and log tail probabilities for losses. The CDF is obtained by integrating the mixture density. KM and censored Gaussian regression with constant variance are comparison baselines.

**Practical meaning and limitations.** MCNet provides a smooth multimodal PDF and direct handling of right censoring, useful for expected costs and bids on a continuous scale. The number of components and training affect stability; a Gaussian mixture still specifies a particular approximation class and is not literally an arbitrary distribution. Tail probabilities can be poorly determined if bids rarely reach the corresponding range. Results in the paper on iPinYou and an industrial DSP do not establish superiority under other mechanisms or prices.

### 6. Ou et al. (2023): Multi-Slot MDLF

**Source:** “Deep Landscape Forecasting in Multi-Slot Real-Time Bidding”

The paper studies an auction with $K$ positions, where the advertiser knows its occupied position and ranking score, but not the full ordering of competitors.

For position $k$, $Z_k$ denotes a random ranking threshold. $F_{Z_k}(z\mid x)$ is the probability of placing in the top $k$ positions with ranking score $z$. The probability of occupying exactly position $k$ is the difference between adjacent CDFs, $F_k-F_{k-1}$. MDLF models loss probabilities $m_{k,l}$ across positions and $L$ price intervals. An LSTM estimates ratios of adjacent values, $h_{k,l}=m_{k,l}/m_{k,l-1}$. Products of these factors recover the survival function, CDF, interval probability mass, and probability of occupying a specified position. The construction keeps probabilities consistent and accounts for dependencies between positions.

An observed position provides information about several thresholds: if a participant occupies position $k$, it made the top $k$ positions but did not occupy any higher position. A loss means it did not make the top $K$ positions. The composite loss accounts for the likelihood of the observed ranking score under the PDF, the probability of the actual occupied position, and binary cross-entropy over the CDF for observed and censored positions. Independent application of single-position methods is discussed as a baseline for comparison with the joint MDLF model.

**Practical meaning and limitations.** The method applies to search-ad auctions and other multi-slot auctions when the ranking rule is known and positions are labeled correctly. Ranking score and actual payment depend on auction rules and ad quality. Discretization and the size of $K\times L$ affect computational cost; training requires enough observations for each position. Metrics can be compared with a single-position CDF forecast only when the event is defined identically.

### 7. Zhou et al. (2021): Deep Distribution Network for First-Price Auctions (DDN)

**Source:** “An Efficient Deep Distribution Network for Bid Shading in First-Price Auctions”

In a first-price auction, the winning DSP pays its own bid. DDN estimates the distribution of minimum winning price $\hat b$, the winning threshold defined by the highest competing bid. The authors distinguish two data disclosure modes: **open (uncensored)**, where the SSP discloses the threshold to all participants regardless of outcome; and **closed (censored)**, where the SSP discloses only the auction outcome. In the first mode the threshold is directly observed; in the second, the outcome indicates only its position relative to the bid.

DDN defines the threshold distribution using a parametric family, whose parameter vector $\alpha(x)$ is estimated by a neural network from auction features $x$. In open mode, parameters are estimated by maximizing the likelihood of observed prices $\hat b_i$:

$$
\max_{\theta}\sum_{i=1}^{n}\log f\!\left(\hat b_i;\alpha_\theta(x_i)\right),
$$

where $f$ is the density of the selected family. In closed mode, the network is trained on outcome $y_i\in\{0,1\}$ (1 for a win) using the win probability $F(b_i;\alpha(x_i))$. The logarithmic loss is

$$
L_{closed}=-\sum_{i=1}^{n}\left[y_i\log F\!\left(b_i;\alpha(x_i)\right)+(1-y_i)\log\!\left(1-F\!\left(b_i;\alpha(x_i)\right)\right)\right].
$$

In §3.3 the authors consider four distribution families $D$: truncated normal, exponential, gamma, and lognormal. Their parameters $\alpha(x)$ are predicted by the model; the architecture could be LR, FM, FwFM, or a deeper network. Thus DDN is not an unrestricted “arbitrary” density: its shape is limited by the selected parametric family.

The distribution is then used to maximize participant expected utility: the difference between impression value and payment, weighted by win probability. For impression value $v$ (written as $V$ in the original) and bid $b$, the authors define

$$
s(b;v,x)=(v-b)F(b\mid x),\qquad
b^*=\arg\max_{0<b<v}(v-b)F(b\mid x).
$$

Golden-section search is used to find $b^*$. Theorem 1 establishes the unique global maximum and absence of a local minimum on $(0,v)$ **only** for four distribution families: truncated normal, exponential, gamma, and lognormal. §2 reviews prior approaches: segment-level distribution, point estimate, LogReg/qFwFM, and WinRate.

**Practical meaning and limitations.** The method applies to advertiser bid selection in a first-price auction, where win probability and payment amount must both be considered. The target depends on how minimum winning price is defined and what the SSP discloses. A distribution of the threshold is not enough by itself; a utility or payoff function and budget constraints are also needed. A second-price payment estimate cannot be directly transferred to a first-price auction, where payment equals $b$.

### 8. Wang et al. (2022): Markov Network and Kaplan–Meier Estimator (KMMN)

**Source:** “Kaplan–Meier Markov network: Learning the distribution of market price by censored data in online advertising”

A segment-level KM estimate does not account for differences between requests within a segment. Let $\tau=(x,b,z,I)$, where $I$ indicates a loss; on a win the price is observed, while on a loss $z$ is unknown and $z\ge b$. In KMMN, probabilities $P(z,\mathrm{win}\mid x)$ and $P(b,\mathrm{lose}\mid x)$ are parameterized by a Markov network, a two-layer product-of-experts model linking the request and bid to price and outcome. A conditional KM estimate of the survival function is recovered from these quantities:

```math
\hat S(b\mid x)=\prod_{j<b}\left(1-\frac{P(z=j,\mathrm{win}\mid x)}{\sum_{z'\ge j}P(z=z',\mathrm{win}\mid x)+\sum_{b'\ge j}P(b=b',\mathrm{lose}\mid x)}\right),
\qquad
p_Z(z=j\mid x)=\hat S(j\mid x)-\hat S(j+1\mid x).
```

The network estimates probabilities from which KM computes a discrete survival function and PMF. Training uses the joint likelihood of observations, and the gradient is estimated using Gibbs sampling. The authors derive $p(z\mid x)$ for a request by summing over possible bids with weights from the empirical prior distribution of bids. This uses the approximation $p(b\mid x)\approx p(b)$.

**Practical meaning and limitations.** KMMN combines nonparametric KM estimation with request features and outcome-probability modeling. It assumes positive integer prices and bids and requires a finite price range. Computational cost depends on the dimensionality of the binary vectors, where one indicates the active category, and on the MCMC sample. The prior-bid approximation may fail when bids depend strongly on $x$. As with KM, estimates of tails beyond the observed range require care. The reported Wasserstein distance, KL, and ANLP values use two public datasets.

### 9. Li et al. (2021 arXiv version): Arbitrary Distribution Modeling (ADM) and Neighborhood Likelihood

**Source:** “Arbitrary Distribution Modeling with Censorship in Real-Time Bidding Advertising”

ADM divides the price range into $N$ equal intervals and estimates a probability-mass vector $\mathrm{pr}_i(i\mid x)$ using softmax. Summing masses below a given price gives the CDF, or win probability. The architecture includes categorical-feature embeddings, numerical features, and low- and high-order interactions. The authors propose a neighborhood likelihood-based loss (NLL).

On a win, the known price $z$ is used in PDF and NLL terms and defines a neighborhood whose boundaries depend on the difference between the bid and price. On a loss, only $z>b$ is known; ADM increases probability mass in the neighborhood to the right of the bid. The objective combines three terms: mass in the observed winning-price interval, mass in a neighborhood of that price, and mass in the right-side neighborhood of a losing bid. The terms are weighted using coefficients $\alpha,\beta$. This objective differs from standard survival-model likelihood.

**Important caveat.** On a loss, condition $z>b$ corresponds to the entire right tail with probability $P(z>b)$ and does not constrain price to a neighborhood close to the bid. The ADM authors justify their approximation with the empirical observation that bids and prices are often close. NLL thus introduces an additional locality assumption that can underestimate the distant tail if loss prices often greatly exceed the bid. Neighborhood widths and weights are important hyperparameters. Softmax does not impose a parametric form on the price distribution, but a finite grid limits its support and resolution.

### 10. Yakovleva et al. (2024): Transformer-Based Price-Distribution Forecasting (TLF)

**Source:** “Bid Landscape Forecasting and Cold Start Problem with Transformers”

TLF estimates the price distribution with a transformer. Price is discretized into intervals $V_l$. The model estimates probabilities $h_{i,l}$ that price falls in each interval, conditional on not having fallen into any previous interval. A vector representation of the request is copied for each price interval, augmented with positional encoding, and passed to a transformer encoder with self-attention. Interval masses and the win probability are calculated from the conditional probabilities:

$$
p_l=h_l\prod_{j<l}(1-h_j),\qquad
W(b_l\mid x)=1-\prod_{j\le l}(1-h_j),\qquad
S(b_l\mid x)=\prod_{j\le l}(1-h_j).
$$

On a finite grid, residual mass after the final interval is $S(b_L)=\prod_{j\le L}(1-h_j)$. A separate tail interval or explicit boundary condition is needed for a normalized PMF over the whole price axis. ADM's softmax normalizes probabilities only across the specified intervals; the tail outside the grid is cut off unless a separate interval is provided. This follows from choosing finite distribution support and is not a verbatim claim by the DLF or TLF authors.

Training uses NLL on the PDF of observed winning prices and binary cross-entropy over the CDF for auction outcomes. A loss is treated as a censored observation without an exact price. Initialization from a pretrained model for the cold-start problem is evaluated separately. Comparison baselines are KM, a survival model, and DLF. On two industrial datasets, the authors reported an average ANLP improvement of 8,75% over DLF and a ROC-AUC improvement of 1,10%.

**Practical meaning and limitations.** Self-attention accounts for relationships across all price intervals, and the distribution is recovered from conditional probabilities. Computational cost depends on price-grid size, while quality depends on the amount of historical data. The cold-start solution relies on transfer learning, pretraining, and similarity between ad distributions. The authors note that runtime is longer than for simple baselines, but consider latency acceptable for their system. Cold-start improvements do not mean the model can be trained without data.

## How to Choose a Method Class

The recommendations in this section are the review author's synthesis of the sources, not verbatim conclusions from any one paper.

1. **Continuous price, with smooth PDF and tail probability of interest.** Start comparisons with censored regression, then consider heteroscedastic regression or MCNet. Check tail calibration separately: win observations alone are insufficient to estimate the distribution.
2. **A flexible discrete form and a CDF for every request are required.** Compare KM in tree leaves (Wang, 2016), KMMN, DLF, and the transformer-based model. The choice depends on data volume, price grid, acceptable latency, and whether an explicit PDF or PMF is needed or win probability is enough.
3. **Prices or events are discrete, and interval-level interpretation matters.** DLF and TLF calculate PMFs from products of conditional-probability factors. Check residual mass beyond the last interval and provide a separate tail interval or boundary condition. ADM normalizes masses within a finite grid using softmax. Its censoring loss relies on an assumption that price is close to the bid; test this on market data.
4. **Categorical segments and limited compute.** A tree plus KM gives an interpretable local estimate when leaves contain enough events. A tree that is too fine produces noisy curves; one that is too coarse is biased toward the overall curve.
5. **Multi-slot placement.** Use a position-based setup such as MDLF rather than independently copying a single-position CDF and taking differences without checking monotonicity. The ranking threshold, position, and payment must be formally consistent with the auction rule.
6. **First-price auction.** First determine whether the minimum winning price is disclosed. Then estimate the distribution of the winning threshold and optimize the bid separately. DDN addresses bid shading relative to impression value; second-price payment formulas do not directly apply.
7. **The publisher sets a floor price and does not fully observe top bids.** In Chahuara et al.'s setup, revenue under different floor prices is forecast while accounting for left censoring of $b_1,b_2$. A DSP CDF accuracy metric alone is insufficient to evaluate such a forecast.

## How to Compare Results Without Methodological Errors

- **Probabilistic accuracy:** log-likelihood and ANLP characterize the likelihood of observations under a model. KL and Wasserstein distance compare distributions when a reliable reference distribution is available. These metrics are not interchangeable.
- **Win-probability calibration:** for each bid, compare forecast $F(b\mid x)$ with the empirical win fraction in a comparable group. Monotonicity and curve calibration alone do not establish density accuracy.
- **Point errors:** MAE on price does not test tail correctness or multimodality. Two forecast distributions with the same mean can imply different expected costs.
- **Evaluation under censoring:** exact $z$ is unknown for losses in a holdout sample; bids must not be treated as observed prices. Use censored likelihood, a proper survival-function estimator, or independently obtained or reconstructed reference values. Historical-data evaluation is subject to bid-policy selection bias: the bid affects whether price is observed.
- **Distribution support and tail:** report the price range, interval partition, number of observations at the upper boundary, and residual probability mass $\prod(1-h)$ beyond the final interval. A conditional-probability model on a finite grid can leave nonzero mass above its upper boundary. Softmax normalizes probabilities only over specified intervals. KM cannot determine the tail beyond the last observed event without an extrapolation model.
- **Comparability:** check whether market side (DSP or SSP), auction format, price and win-event definitions, features, temporal data split, and censoring rules match. The probability of placing in the top $k$ positions in a multi-slot auction cannot be directly compared with the win probability in a single-slot auction.
- **Practical performance:** evaluate latency, cost of building the price grid, data freshness, cost of storing history, and the model's impact on bidding outcomes and ROI separately. Improved ANLP does not guarantee a more effective bidding strategy under a limited budget.
