#!/usr/bin/env python
# Prototype database validation script.  Same args as abe.py.

# Copyright(C) 2011 by John Tobey <John.Tobey@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import sys
import DataStore
import util
import logging
import abe  # for parse_argv

def verify_tx_merkle_hashes(store, logger, chain_id):
    checked, bad = 0, 0
    for block_id, merkle_root, num_tx in store.selectall("""
        SELECT b.block_id, b.block_hashMerkleRoot, b.block_num_tx
          FROM block b
          JOIN chain_candidate cc ON (b.block_id = cc.block_id)
         WHERE cc.chain_id = ?""", (chain_id,)):
        merkle_root = store.hashout(merkle_root)
        tree = []
        for (tx_hash,) in store.selectall("""
            SELECT tx.tx_hash
              FROM block_tx bt
              JOIN tx ON (bt.tx_id = tx.tx_id)
             WHERE bt.block_id = ?
             ORDER BY bt.tx_pos""", (block_id,)):
            tree.append(store.hashout(tx_hash))
        if len(tree) != num_tx:
            logger.warning("block %d: block_num_tx=%d but found %d",
                           block_id, num_tx, len(tree))
        root = merkle(tree, util.double_sha256) or DataStore.NULL_HASH
        if root != merkle_root:
            logger.error("block %d: block_hashMerkleRoot mismatch.",
                         block_id)
            bad += 1
        checked += 1
        if checked % 1000 == 0:
            logger.info("%d Merkle trees, %d bad", checked, bad)
    if checked % 1000 > 0:
        logger.info("%d Merkle trees, %d bad", checked, bad)
    return checked, bad

# Based on CBlock::BuildMerkleTree().
def merkle(hashes, hash_fn):
    while True:
        size = len(hashes)
        if size <= 1:
            break
        out = []
        for i in xrange(0, size, 2):
            i2 = min(i + 1, size - 1)
            out.append(hash_fn(hashes[i] + hashes[i2]))
        hashes = out
    return hashes and hashes[0]

def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    args = abe.parse_argv(argv)
    if not args:
        return 0
    store = DataStore.new(args)
    logger = logging.getLogger("verify")
    checked, bad = 0, 0
    for (chain_id,) in store.selectall("""
        SELECT chain_id FROM chain"""):
        logger.info("checking chain %d", chain_id)
        checked1, bad1 = verify_tx_merkle_hashes(store, logger, chain_id)
        checked += checked1
        bad += bad1
    logger.info("All chains: %d Merkle trees, %d bad", checked, bad)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
