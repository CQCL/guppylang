(module
  ;; --- Function: Return two ---
  (func $two (result i64)
    i64.const 2)

  ;; --- Function: Add two i64s ---
  (func $add (param $a i64) (param $b i64) (result i64)
    (i64.add (local.get $a) (local.get $b))
  )

  ;; --- Function: Identity on floats ---
  (func $fid (param $a f64) (result f64)
    (local.get $a))

  ;; --- Function: Consume a float ---
  (func $eat_float (param $a f64))

  ;; --- Function: Consume a float ---
  (func $nothing)

  ;; --- Exports ---
  (export "add" (func $add))
  (export "two" (func $two))
  (export "fid" (func $fid))
  (export "consume_float" (func $eat_float))
  (export "nothing" (func $nothing))
)
