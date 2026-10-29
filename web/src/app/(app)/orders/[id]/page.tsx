import type { Metadata } from "next";

import { OrderDetail } from "./order-detail";

export const metadata: Metadata = { title: "Order" };

export default function OrderPage() {
  return <OrderDetail />;
}
