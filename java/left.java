public String toString(List<T> l) {
 if (l == null || l.isEmpty()) { return ""; }
 return String.join(",", l);
}
