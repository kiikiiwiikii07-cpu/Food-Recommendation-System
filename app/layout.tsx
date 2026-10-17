import './style.css';
export const metadata = { title: 'Daily Food — your next good meal', description: 'Thoughtful, personal meal ideas for every day.' };
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
