import React from 'react';

// We now accept onHoverTransaction as a prop
const TransactionList = ({ transactions, onHoverTransaction, currentAccountId  }) => {
    if (!transactions || transactions.length === 0) {
        return <p>No specific high-risk transactions were found for this account.</p>;
    }

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
        }).format(amount);
    };

    return (
        <div className="transaction-list">
            {transactions.map((tx, index) => {
                // ✅ Determine if the transaction is incoming or outgoing
                const isIncoming = tx.to === currentAccountId;

                return (
                    <div 
                        key={index} 
                        className="transaction-item"
                        onMouseEnter={() => onHoverTransaction(tx)}
                        onMouseLeave={() => onHoverTransaction(null)}
                    >
                        <div className="transaction-details">
                            <strong>From:</strong> {tx.from} <br />
                            <strong>To:</strong> {tx.to}
                        </div>
                        {/* ✅ Apply the correct class based on the direction */}
                        <div className={isIncoming ? 'transaction-amount in' : 'transaction-amount out'}>
                            {formatCurrency(tx.amount)}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default TransactionList;