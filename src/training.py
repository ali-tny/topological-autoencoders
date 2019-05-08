"""Training classes."""
import torch
from torch.autograd import Variable
from torch.utils.data import DataLoader
from .datasets.splitting import split_dataset
import numpy as np

class TrainingLoop():
    """Training a model using a dataset."""

    def __init__(self, model, dataset, n_epochs, batch_size, learning_rate,
                 weight_decay=1e-5, val_size=0.2, val_frequency=4, callbacks=None):
        """Training of a model using a dataset and the defined callbacks.

        Args:
            model: AutoencoderModel
            dataset: Dataset
            n_epochs: Number of epochs to train
            batch_size: Batch size
            learning_rate: Learning rate
            callbacks: List of callbacks
        """
        self.model = model
        self.dataset = dataset
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.val_size = val_size
        self.val_frequency = val_frequency # per epoch
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.callbacks = callbacks if callbacks else []        

    def _execute_callbacks(self, hook, local_variables):
        for callback in self.callbacks:
            getattr(callback, hook)(**local_variables)

    def on_epoch_begin(self, local_variables):
        """Call callbacks before an epoch begins."""
        self._execute_callbacks('on_epoch_begin', local_variables)

    def on_epoch_end(self, local_variables):
        """Call callbacks after an epoch is finished."""
        self._execute_callbacks('on_epoch_end', local_variables)

    def on_batch_begin(self, local_variables):
        """Call callbacks before a batch is being processed."""
        self._execute_callbacks('on_batch_begin', local_variables)

    def on_batch_end(self, local_variables):
        """Call callbacks after a batch has be processed."""
        self._execute_callbacks('on_batch_end', local_variables)

    # pylint: disable=W0641
    def __call__(self):
        """Execute the training loop."""
        model = self.model
        dataset = self.dataset
        n_epochs = self.n_epochs
        batch_size = self.batch_size
        val_size = self.val_size
        val_frequency = self.val_frequency
        learning_rate = self.learning_rate

        train_loader, validation_loader, test_loader = split_dataset(dataset, val_size, batch_size)
        
        #TODO: is it a problem that we currently don't shuffle in the Dataloader of split_dataset?
        #dataloader = DataLoader(
        #    dataset, batch_size=batch_size, shuffle=True)
        
        n_instances = len(dataset)
        optimizer = torch.optim.Adam(
            model.parameters(), lr=learning_rate,
            weight_decay=self.weight_decay)
        
        n_batches = len(train_loader)
        n_eval_batches = np.floor( n_batches / val_frequency)

        for epoch in range(1, n_epochs+1):
            for batch, data in enumerate(train_loader):
                img, _ = data
                img = Variable(img)  #.cuda()

                # Compute loss
                loss, loss_components = self.model(img)

                # Call callbacks here so we can measure the loss before any
                # optimization has taken place
                local_variables = remove_self(locals())
                if batch == 0:
                    self.on_epoch_begin(local_variables)
                self.on_batch_begin(local_variables)
                del local_variables

                # Optimize
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                # Call callbacks
                self.on_batch_end(remove_self(locals()))

                # Validate val_frequency times per epoch:
                if (batch+1) % n_eval_batches == 0: # batch + 1 as batch starts at 0 
                    val_losses = []
                    for val_batch, val_data in enumerate(validation_loader):
                        img, _ = data
                        img = Variable(img)  #.cuda()
                        # Compute Validation loss
                        val_loss, val_loss_components = self.model(img)
                        val_losses.append(val_loss.item())
                    avg_val_loss = np.array(val_losses).mean() 
                    print(f'Average Validation Loss {avg_val_loss}')
       

                

            self.on_epoch_end(remove_self(locals()))
            
def remove_self(dictionary):
    """Remove entry with name 'self' from dictionary.

    This is useful when passing a dictionary created with locals() as kwargs.

    Args:
        dictionary: Dictionary containing 'self' key

    Returns:
        dictionary without 'self' key

    """
    del dictionary['self']
    return dictionary




