"""A tiny trie supports venue name suggestions as someone types."""

class _TrieNode:
    def __init__(self):
        """Store next letters and names that share this prefix."""
        self.children, self.words = {}, []

class Trie:
    def __init__(self, words=()):
        """Add room names so search can quickly match their prefixes."""
        self.root = _TrieNode()
        for word in words:
            self.insert(word)

    def insert(self, word):
        """Save one room name letter by letter."""
        node = self.root
        node.words.append(word)
        for char in word.lower():
            node = node.children.setdefault(char, _TrieNode())
            node.words.append(word)

    def search(self, prefix):
        """Return the room names that begin with the typed letters."""
        node = self.root
        for char in prefix.lower():
            node = node.children.get(char)
            if node is None:
                return []
        return list(dict.fromkeys(node.words))
