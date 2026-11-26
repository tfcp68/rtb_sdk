from rtb_sdk.schemas import (
    TargetVector,
    FullTagVector,
    RawTag,
    FullTag,
    VocabName,
)
from rtb_sdk.constants import DELIMITER, DataAuctionType

def get_fulltags(vector: TargetVector | FullTagVector) -> FullTagVector:

    result = {}
    for vocab_name, tags in vector['value'].items():
        result[vocab_name] = raw_tag_to_full_tag_list(tags, vocab_name)

    return {'__type': DataAuctionType.FULL_TAG_VECTOR, 'value': result}

def raw_tag_to_full_tag_list(lst: list[RawTag],
                             vocab_name: VocabName
                             ) -> list[FullTag]:

    result = []
    for raw_tag in lst:
        if not is_valid_full_tag(raw_tag):
            full_tag = build_full_tag(vocab_name, raw_tag)
            result.append(full_tag)
        else:
            result.append(raw_tag)
    return result

def build_full_tag(vocab: str,
              tag: RawTag) -> str:
    return vocab + DELIMITER + tag

def is_valid_full_tag(tag: FullTag) -> bool:
    if not isinstance(tag, str):
        return False

    vocab, delimeter, raw_tag = tag.partition(DELIMITER)
    if (vocab == '') or (delimeter == '') or (raw_tag == ''):
        return False

    return True
