import base64
import json
from dataclasses import dataclass
from typing import Union, Dict, Any

import grpc
from google._upb._message import Message
from google.protobuf.json_format import MessageToDict
from typing_extensions import List, Optional, Self
from v4_proto.cosmos.auth.v1beta1 import query_pb2_grpc as auth
from v4_proto.cosmos.auth.v1beta1.auth_pb2 import BaseAccount
from v4_proto.cosmos.auth.v1beta1.query_pb2 import QueryAccountRequest
from v4_proto.cosmos.bank.v1beta1 import query_pb2 as bank_query
from v4_proto.cosmos.bank.v1beta1 import query_pb2_grpc as bank_query_grpc
from v4_proto.cosmos.base.tendermint.v1beta1 import query_pb2 as tendermint_query
from v4_proto.cosmos.base.tendermint.v1beta1 import (
    query_pb2_grpc as tendermint_query_grpc,
)
from v4_proto.cosmos.base.query.v1beta1 import pagination_pb2 as pagination_query
from v4_proto.cosmos.staking.v1beta1 import query_pb2 as staking_query
from v4_proto.cosmos.staking.v1beta1 import query_pb2_grpc as staking_query_grpc
from v4_proto.cosmos.distribution.v1beta1 import query_pb2 as distribution_query
from v4_proto.cosmos.distribution.v1beta1 import (
    query_pb2_grpc as distribution_query_grpc,
)
from v4_proto.cosmos.tx.v1beta1 import service_pb2_grpc
from v4_proto.cosmos.tx.v1beta1.service_pb2 import (
    BroadcastMode,
    BroadcastTxRequest,
    SimulateRequest,
)
from v4_proto.cosmos.gov.v1 import query_pb2 as gov_query
from v4_proto.cosmos.gov.v1 import query_pb2_grpc as gov_query_grpc
from v4_proto.cosmos.tx.v1beta1.tx_pb2 import Tx
from v4_proto.dydxprotocol.accountplus import query_pb2 as accountplus_query
from v4_proto.dydxprotocol.accountplus import query_pb2_grpc as accountplus_query_grpc
from v4_proto.dydxprotocol.bridge import query_pb2 as bridge_query
from v4_proto.dydxprotocol.bridge import query_pb2_grpc as bridge_query_grpc
from v4_proto.dydxprotocol.clob import clob_pair_pb2 as clob_pair_type
from v4_proto.dydxprotocol.clob import (
    equity_tier_limit_config_pb2 as equity_tier_limit_config_type,
)
from v4_proto.dydxprotocol.clob import query_pb2 as clob_query
from v4_proto.dydxprotocol.clob import query_pb2_grpc as clob_query_grpc
from v4_proto.dydxprotocol.clob.order_pb2 import Order, OrderId
from v4_proto.dydxprotocol.clob.query_pb2 import (
    QueryAllClobPairRequest,
    QueryClobPairAllResponse,
)
from v4_proto.dydxprotocol.feetiers import query_pb2 as fee_tier_query
from v4_proto.dydxprotocol.feetiers import query_pb2_grpc as fee_tier_query_grpc
from v4_proto.dydxprotocol.perpetuals import query_pb2_grpc as perpetuals_query_grpc
from v4_proto.dydxprotocol.perpetuals.query_pb2 import (
    QueryAllPerpetualsRequest,
    QueryAllPerpetualsResponse,
    QueryPerpetualRequest,
    QueryPerpetualResponse,
)
from v4_proto.dydxprotocol.prices import market_price_pb2 as market_price_type
from v4_proto.dydxprotocol.prices import query_pb2_grpc as prices_query_grpc
from v4_proto.dydxprotocol.prices.query_pb2 import (
    QueryAllMarketPricesRequest,
    QueryAllMarketPricesResponse,
    QueryMarketPriceRequest,
)
from v4_proto.dydxprotocol.rewards import query_pb2 as rewards_query
from v4_proto.dydxprotocol.rewards import query_pb2_grpc as rewards_query_grpc
from v4_proto.dydxprotocol.stats import query_pb2 as stats_query
from v4_proto.dydxprotocol.stats import query_pb2_grpc as stats_query_grpc
from v4_proto.dydxprotocol.subaccounts import query_pb2 as subaccount_query
from v4_proto.dydxprotocol.subaccounts import query_pb2_grpc as subaccounts_query_grpc
from v4_proto.dydxprotocol.subaccounts import subaccount_pb2 as subaccount_type
from v4_proto.dydxprotocol.subaccounts.query_pb2 import (
    QueryAllSubaccountRequest,
    QueryGetSubaccountRequest,
    QuerySubaccountAllResponse,
)
from v4_proto.dydxprotocol.subaccounts.subaccount_pb2 import SubaccountId
from v4_proto.dydxprotocol.clob.tx_pb2 import OrderBatch
from v4_proto.dydxprotocol.ratelimit import query_pb2 as rate_query
from v4_proto.dydxprotocol.ratelimit import query_pb2_grpc as rate_query_grpc
from v4_proto.dydxprotocol.affiliates import query_pb2 as affiliate_query
from v4_proto.dydxprotocol.affiliates import query_pb2_grpc as affiliate_query_grpc

from dydx_v4_client.network import NodeConfig
from dydx_v4_client.node.authenticators import Authenticator, validate_authenticator
from dydx_v4_client.node.builder import Builder, TxOptions
from dydx_v4_client.node.fee import Coin, Fee, calculate_fee, Denom
from dydx_v4_client.node.message import (
    cancel_order,
    deposit,
    place_order,
    send_token,
    transfer,
    withdraw,
    batch_cancel,
    add_authenticator,
    remove_authenticator,
)
from dydx_v4_client.wallet import Wallet


class CustomJSONDecoder:
    def __init__(self):
        self.decoder = json.JSONDecoder(object_hook=self.decode_dict)

    def decode(self, json_string):
        return self.decoder.decode(json_string)

    @staticmethod
    def decode_base64(value):
        if isinstance(value, str):
            try:
                return list(base64.b64decode(value))
            except (base64.binascii.Error, ValueError):
                return value
        return value

    def decode_dict(self, data):
        if isinstance(data, dict):
            return {k: self.decode_base64(v) for k, v in data.items()}
        return data


@dataclass
class QueryNodeClient:
    channel: grpc.Channel

    @staticmethod
    def transcode_response(response: Message) -> Union[Dict[str, Any], List[Any]]:
        """
        Encodes the response using the custom JSON encoder.

        Args:
            response (Message): The response message to encode.

        Returns:
            Union[Dict[str, Any], List[Any]]: The encoded response.
        """
        response_dict = MessageToDict(response)
        json_string = json.dumps(response_dict)
        return CustomJSONDecoder().decode(json_string)

    async def get_account_balances(
        self, address: str
    ) -> bank_query.QueryAllBalancesResponse:
        """
        Retrieves all account balances for a given address.

        Args:
            address (str): The account address.

        Returns:
            bank_query.QueryAllBalancesResponse: The response containing all account balances.
        """
        stub = bank_query_grpc.QueryStub(self.channel)
        return stub.AllBalances(bank_query.QueryAllBalancesRequest(address=address))

    async def get_account_balance(
        self, address: str, denom: str
    ) -> bank_query.QueryBalanceResponse:
        """
        Retrieves the account balance for a specific denomination.

        Args:
            address (str): The account address.
            denom (str): The denomination of the balance.

        Returns:
            bank_query.QueryBalanceResponse: The response containing the account balance.
        """
        stub = bank_query_grpc.QueryStub(self.channel)
        return stub.Balance(
            bank_query.QueryBalanceRequest(address=address, denom=denom)
        )

    async def get_account(self, address: str) -> BaseAccount:
        """
        Retrieves the account information for a given address.

        Args:
            address (str): The account address.

        Returns:
            BaseAccount: The base account information.
        """
        account = BaseAccount()
        response = auth.QueryStub(self.channel).Account(
            QueryAccountRequest(address=address)
        )
        if not response.account.Unpack(account):
            raise Exception("Failed to unpack account")
        return account

    async def latest_block(self) -> tendermint_query.GetLatestBlockResponse:
        """
        Retrieves the latest block information.

        Returns:
            tendermint_query.GetLatestBlockResponse: The response containing the latest block information.
        """
        return tendermint_query_grpc.ServiceStub(self.channel).GetLatestBlock(
            tendermint_query.GetLatestBlockRequest()
        )

    async def latest_block_height(self) -> int:
        """
        Retrieves the height of the latest block.

        Returns:
            int: The height of the latest block.
        """
        block = await self.latest_block()
        return block.block.header.height

    async def get_user_stats(self, address: str) -> stats_query.QueryUserStatsResponse:
        """
        Retrieves the user stats for a given address.

        Args:
            address (str): The user address.

        Returns:
            stats_query.QueryUserStatsResponse: The response containing the user stats.
        """
        stub = stats_query_grpc.QueryStub(self.channel)
        return stub.UserStats(stats_query.QueryUserStatsRequest(user=address))

    async def get_all_validators(
        self, status: str = ""
    ) -> staking_query.QueryValidatorsResponse:
        """
        Retrieves all validators with an optional status filter.

        Args:
            status (str, optional): The validator status filter. Defaults to an empty string.

        Returns:
            staking_query.QueryValidatorsResponse: The response containing all validators.
        """
        stub = staking_query_grpc.QueryStub(self.channel)
        return stub.Validators(staking_query.QueryValidatorsRequest(status=status))

    async def get_subaccount(
        self, address: str, account_number: int
    ) -> Optional[subaccount_type.Subaccount]:
        """
        Retrieves a subaccount for a given address and account number.

        Args:
            address (str): The owner address.
            account_number (int): The subaccount number.

        Returns:
            Optional[subaccount_type.Subaccount]: The subaccount, if found.
        """
        stub = subaccounts_query_grpc.QueryStub(self.channel)
        response = stub.Subaccount(
            QueryGetSubaccountRequest(owner=address, number=account_number)
        )
        return response.subaccount

    async def get_subaccounts(self) -> QuerySubaccountAllResponse:
        """
        Retrieves all subaccounts.

        Returns:
            QuerySubaccountAllResponse: The response containing all subaccounts.
        """
        stub = subaccounts_query_grpc.QueryStub(self.channel)
        return stub.SubaccountAll(QueryAllSubaccountRequest())

    async def get_clob_pair(self, pair_id: int) -> clob_pair_type.ClobPair:
        """
        Retrieves a CLOB pair by its ID.

        Args:
            pair_id (int): The CLOB pair ID.

        Returns:
            clob_pair_type.ClobPair: The CLOB pair.
        """
        stub = clob_query_grpc.QueryStub(self.channel)
        response = stub.ClobPair(clob_query.QueryGetClobPairRequest(id=pair_id))
        return response.clob_pair

    async def get_clob_pairs(self) -> QueryClobPairAllResponse:
        """
        Retrieves all CLOB pairs.

        Returns:
            QueryClobPairAllResponse: The response containing all CLOB pairs.
        """
        stub = clob_query_grpc.QueryStub(self.channel)
        return stub.ClobPairAll(QueryAllClobPairRequest())

    async def get_price(self, market_id: int) -> market_price_type.MarketPrice:
        """
        Retrieves the market price for a given market ID.

        Args:
            market_id (int): The market ID.

        Returns:
            market_price_type.MarketPrice: The market price.
        """
        stub = prices_query_grpc.QueryStub(self.channel)
        response = stub.MarketPrice(QueryMarketPriceRequest(id=market_id))
        return response.market_price

    async def get_prices(self) -> QueryAllMarketPricesResponse:
        """
        Retrieves all market prices.

        Returns:
            QueryAllMarketPricesResponse: The response containing all market prices.
        """
        stub = prices_query_grpc.QueryStub(self.channel)
        return stub.AllMarketPrices(QueryAllMarketPricesRequest())

    async def get_perpetual(self, perpetual_id: int) -> QueryPerpetualResponse:
        """
        Retrieves a perpetual by its ID.

        Args:
            perpetual_id (int): The perpetual ID.

        Returns:
            QueryPerpetualResponse: The response containing the perpetual.
        """
        stub = perpetuals_query_grpc.QueryStub(self.channel)
        return stub.Perpetual(QueryPerpetualRequest(id=perpetual_id))

    async def get_perpetuals(self) -> QueryAllPerpetualsResponse:
        """
        Retrieves all perpetuals.

        Returns:
            QueryAllPerpetualsResponse: The response containing all perpetuals.
        """
        stub = perpetuals_query_grpc.QueryStub(self.channel)
        return stub.AllPerpetuals(QueryAllPerpetualsRequest())

    async def get_equity_tier_limit_config(
        self,
    ) -> equity_tier_limit_config_type.EquityTierLimitConfiguration:
        """
        Retrieves the equity tier limit configuration.

        Returns:
            equity_tier_limit_config_type.EquityTierLimitConfiguration: The equity tier limit configuration.
        """
        stub = clob_query_grpc.QueryStub(self.channel)
        response = stub.EquityTierLimitConfiguration(
            clob_query.QueryEquityTierLimitConfigurationRequest()
        )
        return response.equity_tier_limit_config

    async def get_delegator_delegations(
        self, delegator_addr: str
    ) -> staking_query.QueryDelegatorDelegationsResponse:
        """
        Retrieves the delegations for a given delegator address.

        Args:
            delegator_addr (str): The delegator address.

        Returns:
            staking_query.QueryDelegatorDelegationsResponse: The response containing the delegator delegations.
        """
        stub = staking_query_grpc.QueryStub(self.channel)
        return stub.DelegatorDelegations(
            staking_query.QueryDelegatorDelegationsRequest(
                delegator_addr=delegator_addr
            )
        )

    async def get_delegator_unbonding_delegations(
        self, delegator_addr: str
    ) -> staking_query.QueryDelegatorUnbondingDelegationsResponse:
        """
        Retrieves the unbonding delegations for a given delegator address.

        Args:
            delegator_addr (str): The delegator address.

        Returns:
            staking_query.QueryDelegatorUnbondingDelegationsResponse: The response containing the delegator unbonding delegations.
        """
        stub = staking_query_grpc.QueryStub(self.channel)
        return stub.DelegatorUnbondingDelegations(
            staking_query.QueryDelegatorUnbondingDelegationsRequest(
                delegator_addr=delegator_addr
            )
        )

    async def get_delayed_complete_bridge_messages(
        self, address: str = ""
    ) -> bridge_query.QueryDelayedCompleteBridgeMessagesResponse:
        """
        Retrieves the delayed complete bridge messages for a given address.

        Args:
            address (str, optional): The address. Defaults to an empty string.

        Returns:
            bridge_query.QueryDelayedCompleteBridgeMessagesResponse: The response containing the delayed complete bridge messages.
        """
        stub = bridge_query_grpc.QueryStub(self.channel)
        return stub.DelayedCompleteBridgeMessages(
            bridge_query.QueryDelayedCompleteBridgeMessagesRequest(address=address)
        )

    async def get_fee_tiers(self) -> fee_tier_query.QueryPerpetualFeeParamsResponse:
        """
        Retrieves the perpetual fee parameters.

        Returns:
            fee_tier_query.QueryPerpetualFeeParamsResponse: The response containing the perpetual fee parameters.
        """
        stub = fee_tier_query_grpc.QueryStub(self.channel)
        return stub.PerpetualFeeParams(fee_tier_query.QueryPerpetualFeeParamsRequest())

    async def get_user_fee_tier(
        self, address: str
    ) -> fee_tier_query.QueryUserFeeTierResponse:
        """
        Retrieves the user fee tier for a given address.

        Args:
            address (str): The user address.

        Returns:
            fee_tier_query.QueryUserFeeTierResponse: The response containing the user fee tier.
        """
        stub = fee_tier_query_grpc.QueryStub(self.channel)
        return stub.UserFeeTier(fee_tier_query.QueryUserFeeTierRequest(user=address))

    async def get_rewards_params(self) -> rewards_query.QueryParamsResponse:
        """
        Retrieves the rewards parameters.

        Returns:
            rewards_query.QueryParamsResponse: The response containing the rewards parameters.
        """
        stub = rewards_query_grpc.QueryStub(self.channel)
        return stub.Params(rewards_query.QueryParamsRequest())

    async def get_authenticators(
        self, address: str
    ) -> accountplus_query.GetAuthenticatorsResponse:
        stub = accountplus_query_grpc.QueryStub(self.channel)
        return stub.GetAuthenticators(
            accountplus_query.GetAuthenticatorsRequest(account=address)
        )

    async def get_node_info(self) -> tendermint_query.GetNodeInfoResponse:
        """
        Query for node info.

        Returns:
            tendermint_query.GetNodeInfoResponse: The response containing the node information.
        """
        return tendermint_query_grpc.ServiceStub(self.channel).GetNodeInfo(
            tendermint_query.GetNodeInfoRequest()
        )

    async def get_delegation_total_rewards(
        self, address: str
    ) -> distribution_query.QueryDelegationTotalRewardsResponse:
        """
        Get all unbonding delegations from a delegator.

        Args:
            address (str): The delegator address

        Returns:
            distribution_query.QueryDelegationTotalRewardsResponse: All unbonding delegations from a delegator.
        """
        return distribution_query_grpc.QueryStub(self.channel).DelegationTotalRewards(
            distribution_query.QueryDelegationTotalRewardsRequest(
                delegator_address=address
            )
        )

    async def get_all_gov_proposals(
        self,
        proposal_status: Optional[str] = None,
        voter: Optional[str] = None,
        depositor: Optional[str] = None,
        key: Optional[bytes] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        count_total: Optional[bool] = False,
        reverse: Optional[bool] = False,
    ) -> gov_query.QueryProposalsResponse:
        """
        Query all gov proposals

        Args:
            proposal_status (Optional[ProposalStatus]): Status of the proposal to filter by.
            voter (Optional[str]): Voter to filter by.
            depositor (Optional[str]): Depositor to filter by.
            key (Optional[byte]): Key to filter by.
            offset (Optional[int]): Offset number.
            limit (Optional[int]): Number of items to retrieve.
            count_total (Optional[bool]): Filter to return total count or not
            reverse (Optional[bool]): Direction of the list
        """
        return gov_query_grpc.QueryStub(self.channel).Proposals(
            gov_query.QueryProposalsRequest(
                proposal_status=proposal_status,
                voter=voter,
                depositor=depositor,
                pagination=pagination_query.PageRequest(
                    key=key,
                    offset=offset,
                    limit=limit,
                    count_total=count_total,
                    reverse=reverse,
                ),
            )
        )

    async def get_withdrawal_and_transfer_gating_status(
        self, perpetual_id: int
    ) -> subaccount_query.QueryGetWithdrawalAndTransfersBlockedInfoResponse:
        """
        Query the status of the withdrawal and transfer gating

        Args:
            perpetual_id (int): The perpetual ID.

        Returns:
            subaccount_query.QueryGetWithdrawalAndTransfersBlockedInfoResponse: Withdrawal and transfer gating status of the perpetual id
        """
        return subaccounts_query_grpc.QueryStub(
            self.channel
        ).GetWithdrawalAndTransfersBlockedInfo(
            subaccount_query.QueryGetWithdrawalAndTransfersBlockedInfoRequest(
                perpetual_id=perpetual_id
            )
        )

    async def get_withdrawal_capacity_by_denom(
        self, denom: str
    ) -> rate_query.QueryCapacityByDenomResponse:
        """
        Query withdrawal capacity by denomination value

        Args:
            denom (str): Denomination identifier

        Returns:
            rate_query.QueryCapacityByDenomResponse: Return withdraw capacity
        """
        return rate_query_grpc.QueryStub(self.channel).CapacityByDenom(
            rate_query.QueryCapacityByDenomRequest(denom=denom)
        )

    async def get_affiliate_info(
        self, address: str
    ) -> affiliate_query.AffiliateInfoResponse:
        """
        Query affiliate information of an address

        Args:
            address (str): Address to get affiliate information of

        Returns:
            affiliate_query.AffiliateInfoResponse: Affiliate information of the address
        """
        return affiliate_query_grpc.QueryStub(self.channel).AffiliateInfo(
            affiliate_query.AffiliateInfoRequest(address=address)
        )

    async def get_referred_by(self, address: str) -> affiliate_query.ReferredByResponse:
        """
        Query to reference information by address

        Args:
            address (str): Address to get referred by information

        Returns:
            affiliate_query.ReferredByResponse: Referred by information
        """
        return affiliate_query_grpc.QueryStub(self.channel).ReferredBy(
            affiliate_query.ReferredByRequest(address=address)
        )

    async def get_all_affiliate_tiers(
        self,
    ) -> affiliate_query.AllAffiliateTiersResponse:
        """
        Query all affiliate tiers

        Returns:
            affiliate_query.AllAffiliateTiersResponse: All affiliate tiers
        """
        return affiliate_query_grpc.QueryStub(self.channel).AllAffiliateTiers(
            affiliate_query.AllAffiliateTiersRequest()
        )

    async def get_affiliate_whitelist(
        self,
    ) -> affiliate_query.AffiliateWhitelistResponse:
        """
        Query whitelisted affiliate information

        Returns:
            affiliate_query.AffiliateWhitelistResponse: List of whitelisted affiliate
        """
        return affiliate_query_grpc.QueryStub(self.channel).AffiliateWhitelist(
            affiliate_query.AffiliateWhitelistRequest()
        )


class SequenceManager:
    def __init__(self, query_node_client: QueryNodeClient):
        self.query_node_client = query_node_client

    async def before_send(self, wallet: Wallet):
        if self.query_node_client:
            account = await self.query_node_client.get_account(wallet.address)
            wallet.sequence = account.sequence

    async def after_send(self, wallet: Wallet):
        if not self.query_node_client:
            wallet.sequence += 1


@dataclass
class MutatingNodeClient(QueryNodeClient):
    builder: Builder
    sequence_manager: SequenceManager = None

    async def broadcast(self, transaction: Tx, mode=BroadcastMode.BROADCAST_MODE_SYNC):
        """
        Broadcasts a transaction.

        Args:
            transaction (Tx): The transaction to broadcast.
            mode (BroadcastMode, optional): The broadcast mode. Defaults to BroadcastMode.BROADCAST_MODE_SYNC.

        Returns:
            The response from the broadcast.
        """
        request = BroadcastTxRequest(
            tx_bytes=transaction.SerializeToString(), mode=mode
        )

        return service_pb2_grpc.ServiceStub(self.channel).BroadcastTx(request)

    async def simulate(self, transaction: Tx):
        """
        Simulates a transaction.

        Args:
            transaction (Tx): The transaction to simulate.

        Returns:
            The response from the simulation.
        """
        request = SimulateRequest(tx=transaction)

        return service_pb2_grpc.ServiceStub(self.channel).Simulate(request)

    async def send(
        self, wallet: Wallet, transaction: Tx, mode=BroadcastMode.BROADCAST_MODE_SYNC
    ):
        """
        Sends a transaction.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            transaction (Tx): The transaction to send.
            mode (BroadcastMode, optional): The broadcast mode. Defaults to BroadcastMode.BROADCAST_MODE_SYNC.

        Returns:
            The response from the broadcast.
        """
        builder = self.builder
        simulated = await self.simulate(transaction)

        fee = self.builder.calculate_fee(simulated.gas_info.gas_used)

        transaction = builder.build_transaction(wallet, transaction.body.messages, fee)

        return await self.broadcast(transaction, mode)

    async def send_message(
        self, wallet: Wallet, message: Message, mode=BroadcastMode.BROADCAST_MODE_SYNC
    ):
        """
        Sends a message.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            message (Message): The message to send.
            mode (BroadcastMode, optional): The broadcast mode. Defaults to BroadcastMode.BROADCAST_MODE_SYNC.

        Returns:
            The response from the broadcast.
        """
        if self.sequence_manager:
            await self.sequence_manager.before_send(wallet)

        response = await self.send(wallet, self.builder.build(wallet, message), mode)

        if self.sequence_manager:
            await self.sequence_manager.after_send(wallet)

        return response

    async def broadcast_message(
        self,
        wallet: Wallet,
        message: Message,
        mode=BroadcastMode.BROADCAST_MODE_SYNC,
        tx_options: Optional[TxOptions] = None,
    ):
        """
        Broadcasts a message.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            message (Message): The message to broadcast.
            mode (BroadcastMode, optional): The broadcast mode. Defaults to BroadcastMode.BROADCAST_MODE_SYNC.
            tx_options (TxOptions, optional): Options for transaction to support authenticators.

        Returns:
            The response from the broadcast.
        """
        if not tx_options and self.sequence_manager:
            await self.sequence_manager.before_send(wallet)

        response = await self.broadcast(
            self.builder.build(wallet, message, tx_options=tx_options),
            mode,
        )

        if not tx_options and self.sequence_manager:
            await self.sequence_manager.after_send(wallet)

        return response

    def build_transaction(self, wallet: Wallet, messages: List[Message], fee: Fee):
        """
        Builds a transaction.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            messages (List[Message]): The list of messages to include in the transaction.
            fee (Fee): The fee to use for the transaction.

        Returns:
            The built transaction.
        """
        return self.builder.build_transaction(wallet, messages, fee.as_proto())

    def build(self, wallet: Wallet, message: Message, fee: Fee):
        """
        Builds a transaction with a single message.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            message (Message): The message to include in the transaction.
            fee (Fee): The fee to use for the transaction.

        Returns:
            The built transaction.
        """
        return self.builder.build(wallet, message, fee.as_proto())

    def calculate_fee(self, gas_used) -> Fee:
        """
        Calculates the fee based on the gas used.

        Args:
            gas_used: The amount of gas used.

        Returns:
            Fee: The calculated fee.
        """
        gas_limit, amount = calculate_fee(gas_used, Denom(self.builder.denomination))
        return Fee(gas_limit, [Coin(amount, self.builder.denomination)])


@dataclass
class NodeClient(MutatingNodeClient):
    manage_sequence: bool = True

    @staticmethod
    async def connect(config: NodeConfig) -> Self:
        client = NodeClient(config.channel, Builder(config.chain_id, config.usdc_denom))
        if client.manage_sequence:
            client.sequence_manager = SequenceManager(QueryNodeClient(client.channel))
        return client

    async def deposit(
        self,
        wallet: Wallet,
        sender: str,
        recipient_subaccount: SubaccountId,
        asset_id: int,
        quantums: int,
    ):
        """
        Deposits funds into a subaccount.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            sender (str): The sender address.
            recipient_subaccount (SubaccountId): The recipient subaccount ID.
            asset_id (int): The asset ID.
            quantums (int): The amount of quantums to deposit.

        Returns:
            The response from the transaction broadcast.
        """
        return await self.send_message(
            wallet, deposit(sender, recipient_subaccount, asset_id, quantums)
        )

    async def withdraw(
        self,
        wallet: Wallet,
        sender_subaccount: SubaccountId,
        recipient: str,
        asset_id: int,
        quantums: int,
    ):
        """
        Withdraws funds from a subaccount.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            sender_subaccount (SubaccountId): The sender subaccount ID.
            recipient (str): The recipient address.
            asset_id (int): The asset ID.
            quantums (int): The amount of quantums to withdraw.

        Returns:
            The response from the transaction broadcast.
        """
        return await self.send_message(
            wallet, withdraw(sender_subaccount, recipient, asset_id, quantums)
        )

    async def send_token(
        self,
        wallet: Wallet,
        sender: str,
        recipient: str,
        quantums: int,
        denomination: str,
    ):
        """
        Sends tokens from one address to another.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            sender (str): The sender address.
            recipient (str): The recipient address.
            quantums (int): The amount of quantums to send.
            denomination (str): The denomination of the token.

        Returns:
            The response from the transaction broadcast.
        """
        return await self.send_message(
            wallet, send_token(sender, recipient, quantums, denomination)
        )

    async def transfer(
        self,
        wallet: Wallet,
        sender_subaccount: SubaccountId,
        recipient_subaccount: SubaccountId,
        asset_id: int,
        amount: int,
    ):
        """
        Transfers funds between subaccounts.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            sender_subaccount (SubaccountId): The sender subaccount ID.
            recipient_subaccount (SubaccountId): The recipient subaccount ID.
            asset_id (int): The asset ID.
            amount (int): The amount to transfer.

        Returns:
            The response from the transaction broadcast.
        """
        return await self.send_message(
            wallet,
            transfer(
                sender_subaccount,
                recipient_subaccount,
                asset_id,
                amount,
            ),
        )

    async def place_order(
        self,
        wallet: Wallet,
        order: Order,
        tx_options: Optional[TxOptions] = None,
    ):
        """
        Places an order.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            order (Order): The order to place.
            tx_options (TxOptions, optional): Options for transaction to support authenticators.

        Returns:
            The response from the transaction broadcast.
        """
        return await self.broadcast_message(
            wallet,
            place_order(order),
            tx_options=tx_options,
        )

    async def cancel_order(
        self,
        wallet: Wallet,
        order_id: OrderId,
        good_til_block: int = None,
        good_til_block_time: int = None,
        tx_options: Optional[TxOptions] = None,
    ):
        """
        Cancels an order.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            order_id (OrderId): The ID of the order to cancel.
            good_til_block (int, optional): The block number until which the order is valid. Defaults to None.
            good_til_block_time (int, optional): The block time until which the order is valid. Defaults to None.
            tx_options (TxOptions, optional): Options for transaction to support authenticators.

        Returns:
            The response from the transaction broadcast.
        """
        return await self.broadcast_message(
            wallet,
            cancel_order(order_id, good_til_block, good_til_block_time),
            tx_options=tx_options,
        )

    async def batch_cancel_orders(
        self,
        wallet: Wallet,
        subaccount_id: SubaccountId,
        short_term_cancels: List[OrderBatch],
        good_til_block: int,
        tx_options: Optional[TxOptions] = None,
    ):
        """
        Batch cancels orders for a subaccount.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction.
            subaccount_id (SubaccountId): The subaccount ID for which to cancel orders.
            short_term_cancels (List[OrderBatch]): List of OrderBatch objects containing the orders to cancel.
            good_til_block (int): The last block the short term order cancellations can be executed at.
            tx_options (TxOptions, optional): Options for transaction to support authenticators.

        Returns:
            The response from the transaction broadcast.
        """
        batch_cancel_msg = batch_cancel(
            subaccount_id=subaccount_id,
            short_term_cancels=short_term_cancels,
            good_til_block=good_til_block,
        )
        return await self.broadcast_message(
            wallet,
            batch_cancel_msg,
            tx_options=tx_options,
        )

    async def add_authenticator(
        self,
        wallet: Wallet,
        authenticator: Authenticator,
    ):
        """
        Adds authenticator to a subaccount.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction or authenticating the request.
            authenticator Authenticator: The authenticator to be added.

        Returns:
            The response from the transaction broadcast.
        """
        if not validate_authenticator(authenticator):
            raise ValueError(
                "Invalid authenticator, please ensure the authenticator permissions are correct."
            )

        add_authenticator_msg = add_authenticator(
            wallet.address,
            authenticator.type,
            authenticator.config,
        )

        return await self.send_message(
            wallet,
            add_authenticator_msg,
        )

    async def remove_authenticator(self, wallet: Wallet, authenticator_id: int):
        """
        Removes authenticator from a subaccount.

        Args:
            wallet (Wallet): The wallet to use for signing the transaction or authenticating the request.
            authenticator_id (int): The authenticator identifier.

        Returns:
            The response from the transaction broadcast.
        """

        remove_authenticator_msg = remove_authenticator(
            wallet.address,
            authenticator_id,
        )

        return await self.send_message(
            wallet,
            remove_authenticator_msg,
        )
