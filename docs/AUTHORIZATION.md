# Authorization rules

## Permission matrix

| Capability | Public | User | Admin |
| --- | ---: | ---: | ---: |
| Register and sign in | Yes | Yes | Yes |
| View market summary | Yes | Yes | Yes |
| View own account and portfolio | No | Yes | Yes |
| Update own display name and password | No | Yes | Yes |
| Record own transactions and view derived holdings | No | Yes | Yes |
| Correct own trades and view own tax lots | No | Yes | Yes |
| Record/correct own stock splits | No | Yes | Yes |
| Manage own watchlist | No | Yes | Yes |
| Record own cash activity and view performance | No | Yes | Yes |
| List all accounts and portfolio totals | No | No | Yes |
| View another account's holdings, transactions, corporate actions, and cash history | No | No | Yes, audited |
| Create an administrator through public registration | No | No | No |

## Security invariants

- Public registration always assigns the `user` role. The client cannot request an admin role.
- Every protected endpoint authenticates the signed session and reloads an active database account.
- Admin endpoints deny non-admin callers with `403 Forbidden` even if they bypass the frontend.
- User portfolio ownership comes from the authenticated account, never a user ID supplied by the browser.
- Detailed admin portfolio access writes `portfolio.view` with the administrator, target account, and time.
- Passwords, password hashes, and session tokens are excluded from API responses and audit records.
- Profile updates always target the signed-in account; the browser cannot provide a different user ID.
- Password changes require the current password, and email updates are not accepted by the profile endpoint.
- Transaction and watchlist ownership always comes from the authenticated account.
- A correction route searches only the caller's portfolio, so another user's transaction is returned as not found.
- Users can void eligible trades but cannot erase ledger history or modify system opening transactions.
- Corporate-action routes resolve the portfolio from the signed-in account; users cannot submit another user's ID.
- Users can void eligible stock splits but cannot erase the original terms, effective time, or correction reason.
- Cash-event and valuation ownership always comes from the authenticated account.
- Admin portfolio, transaction, corporate-action, cash, and accounting access remains read-only.

## Deliberate limits

The broad `admin` role is acceptable for a learning slice but too coarse for a mature financial
application. Future roles should separate support, compliance, security, and account management,
with least-privilege permissions and stronger authentication for privileged users.
