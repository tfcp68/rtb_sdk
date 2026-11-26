"""Interpretable latent campaign hypotheses; no access to seller configuration.

A campaign hypothesis is a conjunction of categorical equalities. Several hypotheses
form a DNF (an OR of conjunctions), equivalently a finite trie over feature tokens.
These are observational hypotheses, not identified advertising accounts.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class Rule:
    terms: tuple[tuple[int, int | tuple[int, ...]], ...]
    probability: float
    support: int
    successes: int
    cooldown: int = 0

    def mask(self, tags):
        result = np.ones(len(tags), dtype=bool)
        for field, value in self.terms:
            result &= np.isin(tags[:, field], value) if isinstance(value, tuple) else tags[:, field] == value
        return result

    def export(self, order, vocabs):
        return dict(targets={order[f]: [vocabs[order[f]][x] for x in (v if isinstance(v, tuple) else (v,))]
                             for f, v in self.terms},
                    probability=self.probability, support=self.support, successes=self.successes,
                    cooldown_seconds=self.cooldown)


class RuleReconstructor:
    def __init__(self, depth=3, max_rules=12, min_support=30, beam_width=12, negative_penalty=2.0,
                 merge_probability=None):
        if min(depth, max_rules, min_support, beam_width) < 1 or negative_penalty <= 0:
            raise ValueError("Search bounds and negative_penalty must be positive")
        self.depth, self.max_rules = depth, max_rules
        self.min_support, self.beam_width = min_support, beam_width
        self.negative_penalty = negative_penalty
        if merge_probability is not None and not 0 <= merge_probability <= 1:
            raise ValueError("merge_probability must be in [0, 1]")
        self.merge_probability = merge_probability
        self.rules: list[Rule] = []

    def _merge(self, n_fields):
        """Join disjoint rectangles differing in one field, using only train rates.

        Rate similarity is evidence for grouping, not proof of common ownership.
        Limit the range within a group to avoid chaining unrelated probabilities.
        """
        if self.merge_probability is None:
            return
        for field in range(n_fields):
            groups, unchanged = {}, []
            for rule in self.rules:
                if field not in dict(rule.terms):
                    unchanged.append(rule)
                    continue
                skeleton = tuple((f, v) for f, v in rule.terms if f != field)
                groups.setdefault(skeleton, []).append(rule)
            for skeleton, group in groups.items():
                clusters = []
                for rule in sorted(group, key=lambda r: r.probability):
                    if not clusters or rule.probability - clusters[-1][0].probability > self.merge_probability:
                        clusters.append([])
                    clusters[-1].append(rule)
                for cluster in clusters:
                    if len(cluster) == 1:
                        unchanged.extend(cluster)
                        continue
                    values = []
                    for rule in cluster:
                        value = dict(rule.terms)[field]
                        values.extend(value if isinstance(value, tuple) else (value,))
                    support = sum(rule.support for rule in cluster)
                    successes = sum(rule.successes for rule in cluster)
                    terms = tuple(sorted(skeleton + ((field, tuple(sorted(set(values)))),)))
                    unchanged.append(Rule(terms, (successes + 1) / (support + 2), support, successes))
            self.rules = unchanged

    def fit(self, tags, y, ts=None, user=None):
        if not len(y):
            raise ValueError("Empty training log")
        self.rules = []
        # Aggregate repeated profiles: bounded search depends on profiles, not log rows.
        profiles, inverse = np.unique(tags, axis=0, return_inverse=True)
        total = np.bincount(inverse, minlength=len(profiles))
        positive = np.bincount(inverse, weights=y, minlength=len(profiles))
        negative = total - positive
        remaining = positive.copy()
        self.base_rate = float(np.mean(y))
        self.background = float((np.sum(y) + 1) / (len(y) + 2))
        for _ in range(self.max_rules):
            root = np.ones(len(profiles), dtype=bool)
            beam = [((), root)]
            candidates = []
            for depth in range(min(self.depth, tags.shape[1]) + 1):
                expanded = []
                for terms, mask in beam:
                    p = float(remaining[mask].sum())
                    n = float(negative[mask].sum())
                    support = int(total[mask].sum())
                    gain = p - self.negative_penalty * n
                    if support >= self.min_support and p > 0:
                        candidates.append((gain, -len(terms), terms, mask))
                    if depth == self.depth:
                        continue
                    # Canonical increasing field order prevents duplicate conjunctions.
                    for field in range(terms[-1][0] + 1 if terms else 0, tags.shape[1]):
                        for value in np.unique(profiles[mask, field]):
                            # Index zero denotes missing data and cannot be targeted by Seller.
                            if value == 0:
                                continue
                            sub = mask & (profiles[:, field] == value)
                            if total[sub].sum() < self.min_support:
                                continue
                            score = remaining[sub].sum() - self.negative_penalty * negative[sub].sum()
                            expanded.append((float(score), terms + ((field, int(value)),), sub))
                expanded.sort(key=lambda item: (-item[0], item[1]))
                beam = [(terms, mask) for _, terms, mask in expanded[:self.beam_width]]
                if not beam:
                    break
            if not candidates:
                break
            gain, _, terms, mask = max(candidates, key=lambda item: (item[0], item[1]))
            if gain <= 0:
                break
            support, successes = int(total[mask].sum()), int(positive[mask].sum())
            self.rules.append(Rule(terms, (successes + 1) / (support + 2), support, successes))
            remaining[mask] = 0
        covered = np.zeros(len(profiles), dtype=bool)
        for rule in self.rules:
            covered |= rule.mask(profiles)
        self.background = float((positive[~covered].sum() + 1) / (total[~covered].sum() + 2))
        self._merge(tags.shape[1])
        return self

    def predict(self, tags, ts=None, user=None, observed=None):
        scores = np.full(len(tags), self.background)
        # Maximum avoids interpreting overlapping hypotheses as independent campaigns.
        covered = np.zeros(len(tags), dtype=bool)
        for rule in self.rules:
            mask = rule.mask(tags)
            scores[mask] = np.where(covered[mask], np.maximum(scores[mask], rule.probability), rule.probability)
            covered |= mask
        return scores


class ValidatedRuleReconstructor(RuleReconstructor):
    """Choose the negative penalty on a chronological training-only tail.

    A fixed penalty of two requires local success rates above 2/3 even when
    frequent targeting matches receive 204 due to availability constraints.
    """
    PENALTIES = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0)

    def fit(self, tags, y, ts=None, user=None):
        if len(y) < 10:
            raise ValueError("Validated model needs >=10 observations")
        if ts is not None and np.any(np.diff(ts) < 0):
            raise ValueError("Log must be chronological")
        cut = int(len(y) * 0.75)
        best = (float("inf"), float("inf"), float("inf"))
        for penalty in self.PENALTIES:
            self.negative_penalty = penalty
            super().fit(tags[:cut], y[:cut])
            loss = float(np.mean((self.predict(tags[cut:]) - y[cut:]) ** 2))
            # Prefer fewer rules, then the stricter penalty on an exact tie.
            candidate = (loss, len(self.rules), -penalty)
            best = min(best, candidate)
        self.selected_negative_penalty = -best[2]
        self.negative_penalty = self.selected_negative_penalty
        return super().fit(tags, y)


class MotifReconstructor(RuleReconstructor):
    """Categorical motif discovery with a noisy-OR latent activation model.

    Inspired by motif seeding/extension and EM in sequence analysis, not a MEME
    implementation: fields have fixed meanings, there is no biological alignment.
    A motif is a conjunction with wildcard positions and optional value lists.
    Positive responses may be explained by several motifs; negatives remain
    evidence against each matching motif. EM estimates activation probabilities
    without hard winner attribution. A BIC-style cost limits motif complexity.
    """

    @staticmethod
    def _addition(mask, prediction, total, positive):
        p, n, yes = prediction[mask], total[mask], positive[mask]
        if not len(p) or yes.sum() == 0:
            return 0.0, 0.0
        no = n - yes
        lo, hi = 0.0, 1 - 1e-6
        # Concave likelihood in the added activation probability.
        for _ in range(16):
            theta = (lo + hi) / 2
            derivative = np.sum(yes * (1 - p) / (p + (1 - p) * theta)) - no.sum() / (1 - theta)
            if derivative > 0:
                lo = theta
            else:
                hi = theta
        theta = (lo + hi) / 2
        gain = np.sum(yes * np.log1p((1 - p) * theta / p)) + no.sum() * np.log1p(-theta)
        return float(gain), theta

    def _em(self, profiles, total, positive):
        masks = np.array([np.ones(len(profiles), dtype=bool)] + [r.mask(profiles) for r in self.rules])
        theta = np.array([self.background] + [r.probability for r in self.rules])
        support = masks @ total
        for _ in range(200):
            p = np.clip(1 - np.prod(1 - masks * theta[:, None], axis=0), 1e-9, 1 - 1e-9)
            # E[activation_j | response=200] = theta_j / P(200).
            new = np.clip(theta * (masks @ (positive / p)) / support, 1e-6, 1 - 1e-6)
            if np.max(np.abs(new - theta)) < 1e-6:
                theta = new
                break
            theta = new
        self.background = float(theta[0])
        for rule, value in zip(self.rules, theta[1:]):
            rule.probability = float(value)

    def fit(self, tags, y, ts=None, user=None):
        if not len(y):
            raise ValueError("Empty training log")
        self.rules = []
        profiles, inverse = np.unique(tags, axis=0, return_inverse=True)
        total = np.bincount(inverse).astype(float)
        positive = np.bincount(inverse, weights=y)
        self.background = float((positive.sum() + 1) / (total.sum() + 2))
        penalty_unit = 0.5 * np.log(max(2, len(y)))

        def evaluate(terms, mask, prediction):
            gain, theta = self._addition(mask, prediction, total, positive)
            complexity = 1 + sum(len(v) if isinstance(v, tuple) else 1 for _, v in terms)
            return gain - penalty_unit * complexity, theta

        for _ in range(self.max_rules):
            prediction = np.clip(self.predict(profiles), 1e-9, 1 - 1e-9)
            beam = [((), np.ones(len(profiles), dtype=bool))]
            best = None
            for _ in range(min(self.depth, tags.shape[1])):
                expanded = []
                for terms, mask in beam:
                    for field in range(terms[-1][0] + 1 if terms else 0, tags.shape[1]):
                        values, supports = np.unique(profiles[mask, field], return_inverse=True)
                        counts = np.bincount(supports, weights=total[mask])
                        for value in values[(values != 0) & (counts >= self.min_support)]:
                            sub = mask & (profiles[:, field] == value)
                            candidate = terms + ((field, int(value)),)
                            score, theta = evaluate(candidate, sub, prediction)
                            expanded.append((score, candidate, sub, theta))
                expanded.sort(key=lambda x: (-x[0], x[1]))
                if not expanded:
                    break
                if best is None or expanded[0][0] > best[0]:
                    best = expanded[0]
                beam = [(terms, mask) for _, terms, mask, _ in expanded[:self.beam_width]]
            if best is None:
                break
            # Extend a seed to a degenerate motif (OR-list) using conditional
            # likelihood, rather than merging by similar marginal response rates.
            score, terms, mask, theta = best
            for field, original in tuple(terms):
                values = {original}
                skeleton = tuple((f, v) for f, v in terms if f != field)
                other_mask = Rule(skeleton, 0, 0, 0).mask(profiles)
                while True:
                    extension = None
                    for value in np.unique(profiles[other_mask, field]):
                        if value == 0 or value in values:
                            continue
                        sub = mask | (other_mask & (profiles[:, field] == value))
                        candidate = tuple(sorted(skeleton + ((field, tuple(sorted(values | {int(value)}))),)))
                        gain, amplitude = evaluate(candidate, sub, prediction)
                        if gain > score and (extension is None or gain > extension[0]):
                            extension = (gain, candidate, sub, amplitude, int(value))
                    if extension is None:
                        break
                    score, terms, mask, theta, value = extension
                    values.add(value)
            if score <= 0:
                break
            self.rules.append(Rule(terms, theta, int(total[mask].sum()), int(positive[mask].sum())))
            self._em(profiles, total, positive)
        # EM can switch off an early, overly broad seed after better motifs are
        # discovered. Remove it by the same likelihood/complexity objective so
        # dormant seeds do not inflate reconstructed targeting or campaign count.
        while self.rules:
            failure = np.full(len(profiles), 1 - self.background)
            for rule in self.rules:
                failure[rule.mask(profiles)] *= 1 - rule.probability
            full = np.clip(1 - failure, 1e-9, 1 - 1e-9)
            removals = []
            for i, rule in enumerate(self.rules):
                without = 1 - failure / (1 - rule.probability * rule.mask(profiles))
                without = np.clip(without, 1e-9, 1 - 1e-9)
                loss = np.sum(positive * np.log(full / without)
                              + (total - positive) * np.log((1 - full) / (1 - without)))
                complexity = 1 + sum(len(v) if isinstance(v, tuple) else 1 for _, v in rule.terms)
                removals.append(penalty_unit * complexity - loss)
            i = int(np.argmax(removals))
            if removals[i] <= 0:
                break
            del self.rules[i]
            self._em(profiles, total, positive)
        return self

    def predict(self, tags, ts=None, user=None, observed=None):
        failure = np.full(len(tags), 1 - self.background)
        for rule in self.rules:
            failure[rule.mask(tags)] *= 1 - rule.probability
        return 1 - failure


class CooldownReconstructor(RuleReconstructor):
    """Per-user READY/BLOCKED automata on top of DNF.

    Cooldowns are chosen on an internal chronological validation tail, then the
    rules are refit on all training data. A 200 is attributed to the highest-rate
    available rule; this assignment is a hypothesis, never a hidden winner label.
    """
    GRID = (0, 30, 120, 300, 900, 3600)

    def _replay(self, tags, ts, user, observed):
        matches = [rule.mask(tags) for rule in self.rules]
        result = np.full(len(tags), self.background)
        ready_at = {}
        for i, (t, u) in enumerate(zip(ts, user)):
            matching = [a for a, mask in enumerate(matches) if mask[i]]
            available = [a for a in matching if t >= ready_at.get((int(u), a), -1)]
            chosen = max(available, key=lambda a: self.rules[a].probability) if available else None
            if chosen is not None:
                result[i] = self.rules[chosen].probability
            elif matching:
                result[i] = min(self.background, 0.02)
            # Output for row i is computed before its response is observed.
            if chosen is not None and observed is not None and observed[i]:
                ready_at[int(u), chosen] = int(t) + self.rules[chosen].cooldown
        return result

    def fit(self, tags, y, ts=None, user=None):
        if ts is None or user is None or len(y) < 10:
            raise ValueError("Cooldown model needs timestamps, users and >=10 observations")
        if np.any(np.diff(ts) < 0):
            raise ValueError("Log must be chronological")
        cut = max(1, int(len(y) * 0.75))
        super().fit(tags[:cut], y[:cut])
        best = (float("inf"), 0)
        for cooldown in self.GRID:
            for rule in self.rules:
                rule.cooldown = cooldown
            scores = self._replay(tags, ts, user, y)
            loss = float(np.mean((scores[cut:] - y[cut:]) ** 2))
            best = min(best, (loss, cooldown))
        self.selected_cooldown = best[1]
        super().fit(tags, y)
        for rule in self.rules:
            rule.cooldown = self.selected_cooldown
        return self

    def predict(self, tags, ts=None, user=None, observed=None):
        return self._replay(tags, ts, user, observed)


def response_metrics(y, probability):
    y = np.asarray(y, dtype=bool)
    probability = np.clip(probability, 1e-9, 1 - 1e-9)
    predicted = probability >= 0.5
    tp = int(np.sum(predicted & y))
    return dict(n=len(y), brier=float(np.mean((probability - y) ** 2)),
                logloss=float(-np.mean(y * np.log(probability) + (~y) * np.log1p(-probability))),
                accuracy=float(np.mean(predicted == y)),
                precision=tp / max(1, int(predicted.sum())), recall=tp / max(1, int(y.sum())))


def compare_targeting(rules, profiles, weights, true_masks, true_ids):
    """Traffic-weighted IoU on an explicit, common profile domain.

    Report best match per rule AND a one-to-one greedy matching at IoU >= .5;
    duplicated hypotheses cannot count as several recovered campaigns.
    """
    inferred = [rule.mask(profiles) for rule in rules]
    matrix = np.zeros((len(rules), len(true_masks)))
    for i, predicted in enumerate(inferred):
        for j, actual in enumerate(true_masks):
            union = weights[predicted | actual].sum()
            matrix[i, j] = float(weights[predicted & actual].sum() / union) if union else 0.0
    rows = []
    for i in range(len(rules)):
        j = int(matrix[i].argmax()) if len(true_masks) else None
        rows.append(dict(hypothesis=i + 1, closest_truth=true_ids[j] if j is not None else None,
                         iou=float(matrix[i, j]) if j is not None else 0.0))
    pairs = sorted(((float(matrix[i, j]), i, j) for i in range(len(rules))
                    for j in range(len(true_masks))), reverse=True)
    used_rules, used_truth, assignments = set(), set(), []
    for iou, i, j in pairs:
        if iou >= 0.5 and i not in used_rules and j not in used_truth:
            used_rules.add(i)
            used_truth.add(j)
            assignments.append(dict(hypothesis=i + 1, truth=true_ids[j], iou=iou))
    predicted_union = np.logical_or.reduce(inferred) if inferred else np.zeros(len(profiles), dtype=bool)
    actual_union = np.logical_or.reduce(true_masks) if true_masks else np.zeros(len(profiles), dtype=bool)
    union = weights[predicted_union | actual_union].sum()
    return dict(best_matches=rows, greedy_assignments=assignments,
                campaign_precision=len(assignments) / max(1, len(rules)),
                campaign_recall=len(assignments) / max(1, len(true_masks)),
                union_iou=float(weights[predicted_union & actual_union].sum() / union) if union else 0.0)
