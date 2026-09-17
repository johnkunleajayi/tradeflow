import { useEffect, useState } from 'react'

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

function App() {
  const [status, setStatus] = useState(null)
  const [wallet, setWallet] = useState(null)
  const [portfolio, setPortfolio] = useState(null)
  const [trades, setTrades] = useState([])
  const [error, setError] = useState(null)

  const fetchDashboard = async () => {
    try {
      const [
        statusResponse,
        walletResponse,
        portfolioResponse,
        tradesResponse,
      ] = await Promise.all([
        fetch(
          `${API_BASE_URL}/automation/rules/BTC/status`,
        ),
        fetch(
          `${API_BASE_URL}/wallet`,
        ),
        fetch(
          `${API_BASE_URL}/portfolio`,
        ),
        fetch(
          `${API_BASE_URL}/trades`,
        ),
      ])

      if (!statusResponse.ok) {
        throw new Error(
          `Automation API request failed: ${statusResponse.status}`,
        )
      }

      if (!walletResponse.ok) {
        throw new Error(
          `Wallet API request failed: ${walletResponse.status}`,
        )
      }

      if (!portfolioResponse.ok) {
        throw new Error(
          `Portfolio API request failed: ${portfolioResponse.status}`,
        )
      }

      if (!tradesResponse.ok) {
        throw new Error(
          `Trades API request failed: ${tradesResponse.status}`,
        )
      }

      const [
        statusData,
        walletData,
        portfolioData,
        tradesData,
      ] = await Promise.all([
        statusResponse.json(),
        walletResponse.json(),
        portfolioResponse.json(),
        tradesResponse.json(),
      ])

      setStatus(statusData)
      setWallet(walletData)
      setPortfolio(portfolioData)
      setTrades(tradesData)
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    fetchDashboard()

    const interval = setInterval(
      fetchDashboard,
      5000,
    )

    return () => clearInterval(interval)
  }, [])

  const formatNgn = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ''
    ) {
      return '—'
    }

    return `₦${Number(value).toLocaleString('en-NG', {
      maximumFractionDigits: 2,
    })}`
  }

  const formatCrypto = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ''
    ) {
      return '—'
    }

    return Number(value).toLocaleString('en-US', {
      maximumFractionDigits: 8,
    })
  }

  const formatTradeTime = (value) => {
    if (!value) {
      return '—'
    }

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) {
      return value
    }

    return date.toLocaleString('en-NG', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getBalance = (currency) => {
    if (!wallet?.balances) {
      return null
    }

    return wallet.balances.find(
      (item) =>
        item.currency?.toUpperCase() ===
        currency.toUpperCase(),
    )
  }

  const availableBalance = (balance) => {
    if (!balance) {
      return null
    }

    const value =
      Number(balance.balance || 0) -
      Number(balance.locked || 0)

    return Math.max(value, 0)
  }

  const ngnBalance = getBalance('NGN')
  const btcBalance = getBalance('BTC')
  const ethBalance = getBalance('ETH')
  const solBalance = getBalance('SOL')

  const recentTrades = [...trades]
    .sort(
      (a, b) =>
        new Date(b.created_at) -
        new Date(a.created_at),
    )
    .slice(0, 10)

  return (
    <div className="min-h-screen bg-[#0b0f14] text-gray-200">
      <header className="sticky top-0 z-10 border-b border-gray-800 bg-[#0b0f14]/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between gap-6 px-6 py-6 sm:px-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-50">
              TradeFlow AI
            </h1>

            <p className="mt-1 text-sm text-gray-500">
              Automated Crypto Trading Dashboard
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-green-900 bg-green-950/30 px-3 py-2 text-xs font-bold tracking-widest text-green-300">
            <span className="h-2 w-2 rounded-full bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.8)]" />
            LIVE
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] px-4 py-8 sm:px-6 lg:py-10">
        <section className="flex flex-col justify-between gap-8 rounded-2xl border border-gray-800 bg-gradient-to-br from-gray-900/95 to-slate-900/80 p-7 shadow-2xl shadow-black/20 sm:p-9 lg:flex-row lg:items-end">
          <div>
            <span className="mb-2 block text-[11px] font-bold tracking-[0.14em] text-gray-500">
              BTC / NGN
            </span>

            <h2 className="text-4xl font-semibold leading-none tracking-tight text-gray-50 sm:text-5xl lg:text-6xl">
              {status
                ? formatNgn(status.current_price)
                : 'Loading...'}
            </h2>

            <p className="mt-3 text-sm text-gray-500">
              Current market price
            </p>
          </div>

          <div className="flex flex-col items-start gap-3 lg:items-end">
            <span
              className={`rounded-full border px-3 py-2 text-[11px] font-extrabold tracking-wider ${
                status?.is_active
                  ? 'border-green-800 bg-green-500/10 text-green-300'
                  : 'border-gray-700 bg-gray-700/10 text-gray-400'
              }`}
            >
              {status?.is_active
                ? 'AUTOMATION ACTIVE'
                : 'STOPPED'}
            </span>

            <span
              className={`text-sm ${
                status?.position_open
                  ? 'text-yellow-400'
                  : 'text-gray-500'
              }`}
            >
              Position:{' '}
              {status?.position_open
                ? 'OPEN'
                : 'CLOSED'}
            </span>
          </div>
        </section>

        {error && (
          <section className="mt-5 flex flex-col gap-1 rounded-xl border border-red-900 bg-red-950/20 px-5 py-4 text-red-300">
            <strong className="text-sm text-red-200">
              Backend connection error
            </strong>

            <span className="text-xs">
              {error}
            </span>
          </section>
        )}

        <section className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label: 'Reference Price',
              value: formatNgn(
                status?.reference_price,
              ),
            },
            {
              label: 'Next BUY Trigger',
              value: formatNgn(
                status?.next_buy_price,
              ),
            },
            {
              label: 'Next SELL Target',
              value: formatNgn(
                status?.next_sell_price,
              ),
            },
            {
              label: 'Minimum Profit',
              value: formatNgn(
                status?.minimum_profit,
              ),
            },
          ].map((metric) => (
            <article
              key={metric.label}
              className="rounded-xl border border-gray-800 bg-[#11161d] p-5"
            >
              <span className="mb-2 block text-xs font-semibold text-gray-500">
                {metric.label}
              </span>

              <strong className="text-xl tracking-tight text-gray-100">
                {metric.value}
              </strong>
            </article>
          ))}
        </section>

        <section className="mt-5 rounded-xl border border-gray-800 bg-[#11161d] p-5 sm:p-6">
          <div className="mb-6 flex items-start justify-between gap-5">
            <div>
              <span className="mb-2 block text-[11px] font-bold tracking-[0.14em] text-gray-500">
                ACCOUNT
              </span>

              <h3 className="text-lg font-semibold tracking-tight text-gray-50">
                Wallet & Portfolio
              </h3>
            </div>

            <span className="rounded-full border border-gray-700 px-3 py-1 text-[11px] font-semibold text-gray-400">
              Quidax
            </span>
          </div>

          <div className="mb-4 rounded-xl border border-gray-800 bg-gray-900/70 p-6">
            <span className="block text-xs font-semibold text-gray-500">
              Total Portfolio Value
            </span>

            <strong className="mt-2 block text-3xl font-semibold tracking-tight text-gray-50 sm:text-4xl">
              {formatNgn(
                portfolio?.total_portfolio_value,
              )}
            </strong>

            <small className="mt-2 block text-xs text-gray-600">
              Live account value
            </small>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <article className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <span className="block text-xs font-semibold text-gray-500">
                Available NGN
              </span>

              <strong className="mt-2 block text-xl text-gray-100">
                {formatNgn(
                  availableBalance(
                    ngnBalance,
                  ),
                )}
              </strong>

              <small className="mt-2 block text-xs text-gray-600">
                Spendable balance
              </small>
            </article>

            <article className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <span className="block text-xs font-semibold text-gray-500">
                BTC Balance
              </span>

              <strong className="mt-2 block text-xl text-gray-100">
                {formatCrypto(
                  btcBalance?.balance,
                )}
              </strong>

              <small className="mt-2 block text-xs text-gray-600">
                Available:{' '}
                {formatCrypto(
                  availableBalance(
                    btcBalance,
                  ),
                )}{' '}
                BTC
              </small>
            </article>

            <article className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <span className="block text-xs font-semibold text-gray-500">
                ETH Balance
              </span>

              <strong className="mt-2 block text-xl text-gray-100">
                {formatCrypto(
                  ethBalance?.balance,
                )}
              </strong>

              <small className="mt-2 block text-xs text-gray-600">
                Available:{' '}
                {formatCrypto(
                  availableBalance(
                    ethBalance,
                  ),
                )}{' '}
                ETH
              </small>
            </article>

            <article className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <span className="block text-xs font-semibold text-gray-500">
                SOL Balance
              </span>

              <strong className="mt-2 block text-xl text-gray-100">
                {formatCrypto(
                  solBalance?.balance,
                )}
              </strong>

              <small className="mt-2 block text-xs text-gray-600">
                Available:{' '}
                {formatCrypto(
                  availableBalance(
                    solBalance,
                  ),
                )}{' '}
                SOL
              </small>
            </article>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex items-center justify-between gap-4 border-t border-gray-800 pt-4">
              <span className="text-xs text-gray-500">
                Cash Value
              </span>

              <strong className="text-sm text-gray-200">
                {formatNgn(
                  portfolio?.cash_balance,
                )}
              </strong>
            </div>

            <div className="flex items-center justify-between gap-4 border-t border-gray-800 pt-4">
              <span className="text-xs text-gray-500">
                Crypto Holdings Value
              </span>

              <strong className="text-sm text-gray-200">
                {formatNgn(
                  portfolio?.holdings_value,
                )}
              </strong>
            </div>
          </div>
        </section>

        <section className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <article className="rounded-xl border border-gray-800 bg-[#11161d] p-6">
            <div className="mb-5 flex items-start justify-between gap-5">
              <div>
                <span className="mb-2 block text-[11px] font-bold tracking-[0.14em] text-gray-500">
                  AUTOMATION
                </span>

                <h3 className="text-lg font-semibold tracking-tight text-gray-50">
                  Trading Strategy
                </h3>
              </div>

              <span
                className={`rounded-full border px-2 py-1 text-[11px] font-bold ${
                  status?.is_active
                    ? 'border-green-800 bg-green-500/10 text-green-300'
                    : 'border-gray-700 text-gray-500'
                }`}
              >
                {status?.is_active
                  ? 'Running'
                  : 'Stopped'}
              </span>
            </div>

            {[
              [
                'Trading pair',
                `${status?.symbol || 'BTC'}/NGN`,
              ],
              [
                'Price step',
                formatNgn(
                  status?.price_step,
                ),
              ],
              [
                'Position',
                status?.position_open
                  ? 'Open'
                  : 'No position',
              ],
              [
                'Minimum profit',
                formatNgn(
                  status?.minimum_profit,
                ),
              ],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between gap-5 border-t border-gray-800 py-4"
              >
                <span className="text-sm text-gray-500">
                  {label}
                </span>

                <strong className="text-right text-sm text-gray-200">
                  {value}
                </strong>
              </div>
            ))}
          </article>

          <article className="rounded-xl border border-gray-800 bg-[#11161d] p-6">
            <div className="mb-5">
              <span className="mb-2 block text-[11px] font-bold tracking-[0.14em] text-gray-500">
                POSITION
              </span>

              <h3 className="text-lg font-semibold tracking-tight text-gray-50">
                Current Trade
              </h3>
            </div>

            {[
              [
                'Entry price',
                formatNgn(
                  status?.entry_price,
                ),
              ],
              [
                'Entry quantity',
                status?.entry_quantity ??
                  '—',
              ],
              [
                'Entry cost',
                formatNgn(
                  status?.entry_cost,
                ),
              ],
              [
                'Target SELL',
                formatNgn(
                  status?.target_sell_price,
                ),
              ],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between gap-5 border-t border-gray-800 py-4"
              >
                <span className="text-sm text-gray-500">
                  {label}
                </span>

                <strong className="text-right text-sm text-gray-200">
                  {value}
                </strong>
              </div>
            ))}
          </article>
        </section>

        <section className="mt-5 rounded-xl border border-gray-800 bg-[#11161d]">
          <div className="flex items-center justify-between gap-5 border-b border-gray-800 px-5 py-5 sm:px-6">
            <div>
              <span className="mb-2 block text-[11px] font-bold tracking-[0.14em] text-gray-500">
                ACTIVITY
              </span>

              <h3 className="text-lg font-semibold tracking-tight text-gray-50">
                Recent Trades
              </h3>
            </div>

            <span className="text-xs text-gray-600">
              Last 10
            </span>
          </div>

          {recentTrades.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-gray-600">
              No trades recorded yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left">
                <thead>
                  <tr className="border-b border-gray-800 text-[11px] font-semibold uppercase tracking-wider text-gray-600">
                    <th className="px-5 py-3 sm:px-6">
                      Time
                    </th>

                    <th className="px-5 py-3">
                      Pair
                    </th>

                    <th className="px-5 py-3">
                      Side
                    </th>

                    <th className="px-5 py-3 text-right">
                      Quantity
                    </th>

                    <th className="px-5 py-3 text-right">
                      Price
                    </th>

                    <th className="px-5 py-3 text-right sm:px-6">
                      Value
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {recentTrades.map((trade) => {
                    const isBuy =
                      trade.side?.toUpperCase() ===
                      'BUY'

                    return (
                      <tr
                        key={trade.id}
                        className="border-b border-gray-800/70 last:border-b-0"
                      >
                        <td className="whitespace-nowrap px-5 py-4 text-xs text-gray-500 sm:px-6">
                          {formatTradeTime(
                            trade.created_at,
                          )}
                        </td>

                        <td className="whitespace-nowrap px-5 py-4 text-sm font-medium text-gray-300">
                          {trade.symbol}/NGN
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-bold ${
                              isBuy
                                ? 'border-green-800 bg-green-500/10 text-green-300'
                                : 'border-red-900 bg-red-500/10 text-red-300'
                            }`}
                          >
                            {trade.side}
                          </span>
                        </td>

                        <td className="whitespace-nowrap px-5 py-4 text-right text-xs text-gray-400">
                          {formatCrypto(
                            trade.quantity,
                          )}
                        </td>

                        <td className="whitespace-nowrap px-5 py-4 text-right text-xs text-gray-400">
                          {formatNgn(
                            trade.price,
                          )}
                        </td>

                        <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-medium text-gray-200 sm:px-6">
                          {formatNgn(
                            trade.total_value,
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="mt-5 flex flex-col items-start justify-between gap-4 text-xs text-gray-600 sm:flex-row sm:items-center">
          <span>
            Dashboard refreshes automatically
            every 5 seconds.
          </span>

          <button
            type="button"
            onClick={fetchDashboard}
            className="rounded-lg border border-gray-700 bg-[#11161d] px-3 py-2 text-gray-300 transition hover:border-gray-600 hover:bg-gray-800"
          >
            Refresh Now
          </button>
        </section>
      </main>
    </div>
  )
}

export default App