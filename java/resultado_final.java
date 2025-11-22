public String toString(List<T> l) {
 if (l == null || l.isEmpty()) { return D; }
 return String.join(",", l);
}
