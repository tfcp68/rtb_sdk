import math

from rtb_sdk.constants.tag_constants import DELIMITER, TAG_OTHER_ENDING, TAG_EMPTY_ENDING
from rtb_sdk.schemas.auction_schemas import AdId, VocabName, RawTag, FullTag
from rtb_sdk.schemas.balancer_schemas import InnerVocabs


def build_full_tag(vocab: str, raw_tag: str) -> str:
    return vocab + DELIMITER + raw_tag


def build_full_tag_other(vocab: str) -> str:
    return vocab + TAG_OTHER_ENDING


def build_full_tag_empty(vocab: str) -> str:
    return vocab + TAG_EMPTY_ENDING


def get_vocab_name(tag: str) -> str:
    vocab, _, _ = tag.partition(DELIMITER)
    return vocab


def get_raw_tag(tag: str) -> str:
    _, _, raw_tag = tag.partition(DELIMITER)
    return raw_tag


def raw_tag_dict_to_full_tag_dict(
    d: dict[VocabName, list[RawTag]],
) -> InnerVocabs:
    return {
        vocab: [build_full_tag(vocab, raw_tag) for raw_tag in tags]
        for vocab, tags in d.items()
    }


def outer_tag_probabilities_to_inner(
    d: dict[VocabName, dict[RawTag, float]],
) -> dict[FullTag, float]:
    return {
        build_full_tag(vocab, raw_tag): prob
        for vocab, tags in d.items()
        for raw_tag, prob in tags.items()
    }


def build_tag_to_vocab_hash(
    vocabs: InnerVocabs,
) -> dict[FullTag, VocabName]:
    result: dict[FullTag, VocabName] = {}
    for vocab_name, tags in vocabs.items():
        for tag in tags:
            result[tag] = vocab_name
    return result


def build_new_old_tags_hashes(
    old_vocabs: InnerVocabs,
    new_vocabs: InnerVocabs,
) -> tuple[dict[FullTag, list[FullTag]], dict[FullTag, FullTag]]:
    # Build a bidirectional mapping between old and new tags.
    # After narrowing the dictionary (build_new_vocabs), tags not used by any
    # ad are merged under the TAG_OTHER tag of that dictionary.
    #
    # cross = tags that remained unchanged in the new dictionary → map to themselves.
    # old - cross = tags that were "absorbed" by TAG_OTHER → old_to_new[tag] = OTHER,
    #               new_to_old[OTHER] = list of absorbed tags.
    new_to_old: dict[FullTag, list[FullTag]] = {}
    old_to_new: dict[FullTag, FullTag] = {}

    for vocab, old_vocab in old_vocabs.items():
        old_set = set(old_vocab)
        new_set = set(new_vocabs.get(vocab, []))

        cross = old_set & new_set
        for tag in cross:
            old_to_new[tag] = tag
            new_to_old[tag] = [tag]

        if len(cross) < len(old_set):
            other_tag = build_full_tag_other(vocab)
            other_in_vocab = old_set - cross

            new_to_old[other_tag] = []
            for tag in other_in_vocab:
                old_to_new[tag] = other_tag
                new_to_old[other_tag].append(tag)

    return new_to_old, old_to_new


def build_new_probabilities(
    new_vocabs: InnerVocabs,
    vocabs: InnerVocabs,
    new_to_old_tags: dict[FullTag, list[FullTag]],
    tag_probabilities: dict[FullTag, float],
) -> dict[FullTag, float]:
    # Recompute probabilities for the compressed dictionary.
    # Each new tag gets the sum of the probabilities of all old tags that
    # were merged into it (via new_to_old_tags). This is correct: if 'geo:ekb' and 'geo:nsk'
    # were merged into 'geo:OTHER', then P(OTHER) = P(ekb) + P(nsk).
    #
    # The probability of TAG_OTHER is computed as the remainder up to 1.0, so that the sum
    # of probabilities over the dictionary stays equal to 1.
    result_probs: dict[FullTag, float] = {}

    for vocab in vocabs:
        other_tag = build_full_tag_other(vocab)
        vocab_prob_sum = 0.0

        if vocab in new_vocabs:
            for tag in new_vocabs[vocab]:
                if tag != other_tag:
                    tags = new_to_old_tags[tag]
                    tags_sum = sum(tag_probabilities.get(t, 0.0) for t in tags)
                    result_probs[tag] = tags_sum
                    vocab_prob_sum += tags_sum

        if vocab_prob_sum < 1.0:
            result_probs[other_tag] = 1.0 - vocab_prob_sum

    return result_probs


def build_new_ads_tags(
    ads_vocabs_tags: dict[AdId, dict[VocabName, list[FullTag]]],
    vocabs: InnerVocabs,
    new_vocabs: InnerVocabs,
) -> dict[AdId, dict[VocabName, list[FullTag]]]:
    # Update the ads' tags for the compressed dictionary.
    # If the ad covers the whole dictionary (all tags) or specified no tags
    # for the given dictionary — assign the full new_vocab (the ad is "not targeted"
    # at specific tags in this dictionary).
    # If the ad specified only some of the tags — keep the original ones.
    result: dict[AdId, dict[VocabName, list[FullTag]]] = {}

    for ad, ad_vocabs in ads_vocabs_tags.items():
        result[ad] = {}
        for vocab, vocabs_vocab in vocabs.items():
            if vocab in ad_vocabs:
                length = len(ad_vocabs[vocab])
                if (length == 0) or (length == len(vocabs_vocab)):
                    # Full or zero coverage — take the entire compressed dictionary
                    result[ad][vocab] = new_vocabs[vocab]
                else:
                    # Partial coverage — the ad's specific tags are kept
                    result[ad][vocab] = ad_vocabs[vocab]
            else:
                result[ad][vocab] = new_vocabs[vocab]

    return result


def count_ads_probabilities(
    ads_vocabs_tags: dict[AdId, dict[VocabName, list[FullTag]]],
    vocabs: InnerVocabs,
    tag_probabilities: dict[FullTag, float],
) -> dict[AdId, float]:
    # P(ad) = ∏_vocab Σ_{tag ∈ ad ∩ vocab} P(tag)
    #
    # For each dictionary sum the probabilities of the ad's tags in it —
    # this is the probability that a request hits at least one of the ad's tags
    # in the given dictionary (tags within a dictionary are mutually exclusive).
    # The product over dictionaries gives the final probability that the request
    # matches the ad across all dimensions simultaneously.
    result: dict[AdId, float] = {}

    for ad_id, ad_vocabs_tags in ads_vocabs_tags.items():
        tmp: dict[VocabName, float] = {}
        for vocab in vocabs:
            if vocab in ad_vocabs_tags:
                vocab_tags = ad_vocabs_tags[vocab]
                tmp[vocab] = sum(tag_probabilities.get(tag, 0.0) for tag in vocab_tags)
            else:
                tmp[vocab] = 0.0

        result[ad_id] = math.prod(tmp.values())

    return result
