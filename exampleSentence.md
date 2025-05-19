### ✅ **Full chain — all services resolvable**

```text
I’m user 2345, and I want to rent a van in MUC from May 10 to May 14.
```

Triggers:

* `rental-service` (location, dates)
* `customer-service` (from `customer_id`)
* `pricing-service` (vehicle\_type, days, customer\_tier)
* `insurance-service` (vehicle\_type, customer\_tier)

---

### ⚠️ **Partial: No customer ID → skips `customer-service`, `pricing-service`, `insurance-service`**

```text
I want to rent a sedan in Berlin between June 5 and June 10.
```

Triggers only:

* `rental-service` (location, dates)
  Skips others due to missing `customer_id` → no `customer_tier`

---

### ⚠️ **Partial: Mentions customer ID, but no vehicle → skips `pricing-service`, `insurance-service`**

```text
I’m user 2345, and I want to rent a car in Hamburg next week.
```

Triggers:

* `customer-service`
* Possibly `rental-service` if dates can be parsed
  Skips:
* `pricing-service`, `insurance-service` (missing `vehicle_type`)

---

### ⚠️ **Mentions tier directly — no customer-service needed**

```text
I’m a platinum customer and need an SUV in Munich from 2025-07-01 to 2025-07-04.
```

Triggers:

* `rental-service`
* `pricing-service`
* `insurance-service`
  Skips:
* `customer-service` — not needed since `customer_tier` is provided

---

### ❌ **Under-specified: only vague intent**

```text
Can you give me a price for a rental?
```

Skips most services (missing location, vehicle, date, tier, etc.)

---

### ⚠️ **Tricky one — vehicle and customer ID only**

```text
I’m user 7777 and looking to rent a truck.
```

Triggers:

* `customer-service`
  Skips:
* `rental-service`, `pricing-service`, `insurance-service` (missing location, date)

