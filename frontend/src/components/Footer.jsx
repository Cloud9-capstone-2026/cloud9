export default function Footer() {
  return (
    <footer style={styles.footer}>
      <span style={styles.text}>© 2026 EWHA capstone Cloud9. All rights reserved.</span>
      <button style={styles.contactBtn}>Contact Us</button>
    </footer>
  );
}

const styles = {
  footer: {
    flexShrink: 0,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 28px',
    background: '#0F172A',
    minWidth: 976,
  },
  text: {
    fontSize: 12,
    color: '#94A3B8',
  },
  contactBtn: {
    background: 'none',
    border: 'none',
    fontSize: 12,
    color: '#94A3B8',
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
  },
};
