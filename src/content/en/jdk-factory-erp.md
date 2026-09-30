> This is what Perennia means by building technology around the business.

JDK Factory ERP was built for one manufacturing business, around its own operational workflow. It is an example of how we work — not an off-the-shelf product.

## The business need

A manufacturing business needs its commercial, procurement, inventory, production, delivery and payment processes to work together reliably. Every department should work from the same orders, the same stock and the same rules, instead of passing information between separate tools.

## The approach

We mapped the operational workflow first: how an enquiry becomes a quotation, and how an order is checked, sourced, produced, delivered and paid for. Each module was specified before it was built, and the rules the business runs on — who approves what, and when an order may be delivered — were built into the system rather than left to memory.

## The solution: one connected workflow

[[workflow: Sales → Feasibility → Quotation → Order → Procurement → Inventory → Production → Delivery → Payment]]

Each stage hands on to the next inside the same system:

- **Sales** — leads and customers, each assigned to a salesperson, with activity history.
- **Feasibility** — each quotation is checked against stock and production; exceptions go to an Admin for a decision.
- **Quotations** — price bands with approval when a price falls outside them, a credit check on acceptance, and a readiness check before conversion.
- **Orders** — an accepted quotation becomes a sales order and is handed off automatically; contracts can be called off in parts.
- **Procurement** — RFQs to suppliers, approvals, purchase orders and goods receiving.
- **Inventory** — raw-material and finished-goods stock, moved by receiving, allocation and delivery.
- **Production** — production requirements, plans and schedules across production lines and machines, based on bills of materials.
- **Delivery** — delivery instructions and fulfilment against each order, within a set delivery allowance.
- **Payments** — Finance records and confirms payment; an order is completed only once payment is confirmed.

![An accepted quotation in JDK Factory ERP, showing the credit check and readiness to become a sales order](/static/case-studies/jdk-erp/quotation.png "An accepted quotation: credit check passed, ready to become a sales order.")

## Rules the business runs on

Screens alone don't make an ERP. The system enforces the operational rules:

- An order to be paid before delivery cannot be delivered until Finance confirms payment — the server refuses it for everyone.
- Access follows responsibility: salespeople see their own customers, managers their team's, and admins everything; each procurement action needs its own permission.
- Documents are numbered once and never reused, and changes are kept in a history.

![The warehouse view of an order that is not yet released for delivery because Finance has not confirmed payment](/static/case-studies/jdk-erp/delivery-gate.png "The warehouse view: not released for delivery until Finance confirms payment.")

![The finance view of the same order after payment is confirmed and delivery is released](/static/case-studies/jdk-erp/finance.png "Finance confirms the payment, and the order is released for delivery.")

![A completed sales order linked to its quotation, finance record, deliveries and returns](/static/case-studies/jdk-erp/sales-order.png "The completed order, linked to its quotation, finance record, deliveries and returns.")

*Screens show the system's demonstration data, not customer data.*

The system also works the way the business does locally: Kuwait time, amounts in KWD to three decimals, and DD-MM-YYYY dates.

## What it demonstrates

- Understanding a manufacturing workflow end to end before writing software
- Connecting sales, procurement, stores, production and finance through one system
- Business-specific software rather than a generic package
- Operational rules and approvals built into the system
- One shared record of each order in place of hand-offs between separate tools
- Technology built around real-world business requirements

## Start with your own workflow

Let's understand the problem before deciding what to build.

[[cta]]
