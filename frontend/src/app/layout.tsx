import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BuildTwin Vision",
  description: "Evidence-first 4D construction intelligence"
};

export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
