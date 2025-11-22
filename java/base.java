public String toString(List<T> l) {
 if (l.size() == 0) { return ""; }
 return String.join(",", l);
}
