from avantis_trader_sdk import TraderClient
from avantis_trader_sdk.types import TradeInput, TradeInputOrderType
from avantis_trader_sdk.config import CONTRACT_ADDRESSES
from eth_account import Account


class AvantisTrader:
    """
    Class for trading on Avantis DEX.
    Handles opening and closing positions with LIMIT orders.
    """

    def __init__(self, rpc_url: str, private_key: str):
        self.client = TraderClient(rpc_url)
        self.client.set_local_signer(private_key)
        self.private_key = private_key
        self.wallet = Account.from_key(private_key).address
        self.trading_address = CONTRACT_ADDRESSES["Trading"]
        print(f"[TRADER] Wallet: {self.wallet}")

    async def check_and_approve_usdc(self, amount: float) -> bool:
        """
        Check USDC allowance and approve if needed.

        Args:
            amount: Amount of USDC to approve (in USDC, not wei)

        Returns:
            True if approved or already has allowance
        """
        # Check current allowance
        allowance = await self.client.read_contract(
            "USDC", "allowance", self.wallet, self.trading_address, decode=False
        )
        allowance_usdc = allowance / 10**6

        if allowance_usdc >= amount:
            print(f"[APPROVE] USDC allowance OK: {allowance_usdc:.2f}")
            return True

        print(f"[APPROVE] Current allowance: {allowance_usdc:.2f}, need: {amount:.2f}")
        print("[APPROVE] Approving USDC for Trading contract...")

        # Approve max uint256
        max_amount = 2**256 - 1

        # Build approve transaction
        usdc_contract = self.client.contracts["USDC"]
        tx = await usdc_contract.functions.approve(
            self.trading_address, max_amount
        ).build_transaction({
            "from": self.wallet,
            "nonce": await self.client.get_transaction_count(self.wallet),
            "gasPrice": await self.client.get_gas_price(),
        })

        # Sign and send
        receipt = await self.client.sign_and_get_receipt(tx)
        tx_hash = receipt["transactionHash"].hex()
        print(f"[APPROVE] USDC approved: {tx_hash}")
        return True

    async def place_limit_order(
        self,
        pair_index: int,
        is_long: bool,
        collateral: float,
        leverage: int,
        limit_price: float,
        tp_price: float,
        sl_price: float,
        direction: str = "BELOW",
        dry_run: bool = True
    ) -> str:
        """
        Place a LIMIT order on Avantis.

        Args:
            pair_index: Index of the trading pair (0 = BTC/USD)
            is_long: True for LONG, False for SHORT
            collateral: Collateral in USDC
            leverage: Leverage multiplier
            limit_price: Limit price for order execution
            tp_price: Take profit price
            sl_price: Stop loss price
            dry_run: If True, don't send transaction

        Returns:
            Transaction hash or "DRY_RUN"
        """
        side = "LONG" if is_long else "SHORT"

        if dry_run:
            print(f"[DRY-RUN] Placing {side} LIMIT order:")
            print(f"  Pair Index: {pair_index}")
            print(f"  Collateral: {collateral} USDC")
            print(f"  Leverage: {leverage}x")
            print(f"  Limit Price: {limit_price:.2f}")
            print(f"  TP Price: {tp_price:.2f}")
            print(f"  SL Price: {sl_price:.2f}")
            return "DRY_RUN"

        # Create trade input
        trade_input = TradeInput(
            trader=self.wallet,
            pair_index=pair_index,
            is_long=is_long,
            leverage=leverage,
            collateral_in_trade=collateral,
            open_price=limit_price,
            tp=tp_price,
            sl=sl_price
        )

        # Choose order type based on direction and side
        # BELOW (waiting for price drop): LONG=LIMIT, SHORT=STOP_LIMIT
        # ABOVE (waiting for price rise): LONG=STOP_LIMIT, SHORT=LIMIT
        if direction == "BELOW":
            order_type = TradeInputOrderType.LIMIT if is_long else TradeInputOrderType.STOP_LIMIT
        else:  # ABOVE
            order_type = TradeInputOrderType.STOP_LIMIT if is_long else TradeInputOrderType.LIMIT

        tx = await self.client.trade.build_trade_open_tx(
            trade_input=trade_input,
            trade_input_order_type=order_type,
            slippage_percentage=1
        )

        # Sign and send
        receipt = await self.client.sign_and_get_receipt(tx)

        tx_hash = receipt["transactionHash"].hex()
        order_type_name = "LIMIT" if order_type == TradeInputOrderType.LIMIT else "STOP-LIMIT"
        print(f"[{side}] {order_type_name} at ${limit_price:.2f}: {tx_hash}")
        return tx_hash

    async def cancel_order(
        self,
        pair_index: int,
        trade_index: int,
        dry_run: bool = True
    ) -> str:
        """
        Cancel a pending LIMIT order on Avantis.

        Args:
            pair_index: Index of the trading pair
            trade_index: Index of the order to cancel
            dry_run: If True, don't send transaction

        Returns:
            Transaction hash or "DRY_RUN"
        """
        if dry_run:
            print(f"[DRY-RUN] Cancelling order:")
            print(f"  Pair Index: {pair_index}")
            print(f"  Trade Index: {trade_index}")
            return "DRY_RUN"

        # Build cancel transaction
        tx = await self.client.trade.build_order_cancel_tx(
            trader=self.wallet,
            pair_index=pair_index,
            trade_index=trade_index
        )

        # Sign and send
        receipt = await self.client.sign_and_get_receipt(tx)

        tx_hash = receipt["transactionHash"].hex()
        print(f"[CANCEL] Order cancelled: {tx_hash}")
        return tx_hash

    async def close_position(
        self,
        pair_index: int,
        trade_index: int,
        collateral_to_close: float,
        dry_run: bool = True
    ) -> str:
        """
        Close a position on Avantis.

        Args:
            pair_index: Index of the trading pair
            trade_index: Index of the trade to close
            collateral_to_close: Amount of collateral to close
            dry_run: If True, don't send transaction

        Returns:
            Transaction hash or "DRY_RUN"
        """
        if dry_run:
            print(f"[DRY-RUN] Closing position:")
            print(f"  Pair Index: {pair_index}")
            print(f"  Trade Index: {trade_index}")
            print(f"  Collateral to close: {collateral_to_close} USDC")
            return "DRY_RUN"

        # Build close transaction
        tx = await self.client.trade.build_trade_close_tx(
            trader=self.wallet,
            pair_index=pair_index,
            trade_index=trade_index,
            collateral_to_close=collateral_to_close
        )

        # Sign and send
        receipt = await self.client.sign_and_get_receipt(tx)

        tx_hash = receipt["transactionHash"].hex()
        print(f"[CLOSE] Position closed: {tx_hash}")
        return tx_hash

    async def get_open_trades(self):
        """
        Get all open trades for the wallet.

        Returns:
            Tuple of (trades, pending_orders)
        """
        trades, pending_orders = await self.client.trade.get_trades(self.wallet)
        return trades, pending_orders
