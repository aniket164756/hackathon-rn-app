---
description: "React Native, TypeScript, styling, testing, and error handling code quality rules for this project. Load when reviewing or writing src/ code."
---

# React Native Conventions

| Rule | Severity |
|---|---|
| Use FlatList/SectionList over ScrollView+map for lists | Critical |
| Always provide `keyExtractor` on FlatList | Critical |
| Wrap expensive calculations in `useMemo` | High |
| Wrap callbacks passed to children in `useCallback` | High |
| Custom hooks must be prefixed with `use` | Critical |
| Always return cleanup from `useEffect` when registering listeners/timers | Critical |
| Do not call hooks conditionally | Critical |
| Place all hook calls at the top of the component | High |
| Do not pass `async` function directly to `useEffect` | Critical |

**FlatList checklist**: `keyExtractor` ✓ · `renderItem` not inline ✓ · `initialNumToRender` set ✓ · `data` not a new array literal on each render ✓

**useEffect async pattern**:
```tsx
// Bad
useEffect(async () => { ... }, []);

// Good
useEffect(() => {
  const load = async () => { ... };
  load();
}, []);
```

**useEffect cleanup pattern**:
```tsx
useEffect(() => {
  const sub = AppState.addEventListener('change', handler);
  return () => sub.remove();
}, []);
```

---

# Styling Conventions

| Rule | Severity |
|---|---|
| No inline style objects — use `StyleSheet.create()` | Critical |
| No hardcoded hex/rgba colour values — import from `core-constants/palette.constant.ts` | Critical |

```tsx
// Bad
<View style={{ flex: 1, backgroundColor: '#3B82F6' }}>

// Good
import PALETTE from '../core-constants/palette.constant';
const styles = StyleSheet.create({ container: { flex: 1, backgroundColor: PALETTE.primary } });
<View style={styles.container}>
```

---

# TypeScript Conventions

| Rule | Severity |
|---|---|
| No `any` type — use `unknown` + type guards or precise types | Critical |
| Prefer `interface` over `type` for object shapes | Low |
| Non-null assertion `!` must have an explanatory comment | High |
| No duplicate variable declarations or variable shadowing | Critical |

---

# Testing Conventions

| Rule | Severity |
|---|---|
| Every component must have a collocated `.test.tsx` file | Critical |
| Async tests must use `waitFor` / `findBy*` — no `setTimeout` hacks | High |

---

# Error Handling Conventions

| Rule | Severity |
|---|---|
| Every `async` API call must be wrapped in `try/catch` | Critical |

```tsx
// Good
const fetchUser = async () => {
  try {
    const user = await api.getUser(id);
    setUser(user);
  } catch (error) {
    setError(error instanceof Error ? error.message : 'Unknown error');
  }
};
```
