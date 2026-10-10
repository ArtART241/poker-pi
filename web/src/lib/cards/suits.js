// Suit shapes as SVG paths in a 100 x 100 box (drawn, not font glyphs, so they never turn into emoji).
export const SUIT_PATH = {
  h: "M50 92 C50 92 4 62 4 31 C4 15 16 4 30 4 C40 4 47 10 50 19 C53 10 60 4 70 4 C84 4 96 15 96 31 C96 62 50 92 50 92 Z",
  d: "M50 2 C58 18 72 36 90 50 C72 64 58 82 50 98 C42 82 28 64 10 50 C28 36 42 18 50 2 Z",
  s: "M50 3 C50 3 94 34 94 60 C94 75 83 83 71 83 C63 83 56 79 53 73 C54 83 58 91 66 97 L34 97 C42 91 46 83 47 73 C44 79 37 83 29 83 C17 83 6 75 6 60 C6 34 50 3 50 3 Z",
  c: "M50 6 C61 6 69 15 69 26 C69 31 67 35 64 39 C67 37 71 36 75 36 C86 36 95 45 95 57 C95 69 86 78 75 78 C65 78 57 72 54 64 C54 79 59 89 67 97 L33 97 C41 89 46 79 46 64 C43 72 35 78 25 78 C14 78 5 69 5 57 C5 45 14 36 25 36 C29 36 33 37 36 39 C33 35 31 31 31 26 C31 15 39 6 50 6 Z",
};

export const RED = "#c4161c";
export const BLACK = "#16161a";

export const isRed = (suit) => suit === "h" || suit === "d";
export const rankLabel = (rank) => (rank === "T" ? "10" : rank);
export const suitName = { h: "hearts", d: "diamonds", c: "clubs", s: "spades" };
export const rankName = { T: "10", J: "jack", Q: "queen", K: "king", A: "ace" };
