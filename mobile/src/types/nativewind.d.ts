/**
 * NativeWind v4 の `className` prop 型拡張。
 *
 * デフォルトでは `<View>` 等の RN コンポーネントは `className` を受け取らないが、
 * NativeWind の `jsxImportSource: 'nativewind'` で全コンポーネントに付与される。
 * tsc の型エラー抑止のためアンビエント宣言する。
 */
/// <reference types="nativewind/types" />
